"""Extension discovery — clone repo and parse build.gradle metadata."""

from __future__ import annotations

import base64
import re
import subprocess
from pathlib import Path

from anime_ext_test.config import Config
from anime_ext_test.models import ExtensionMeta

# Regex to match the ext { ... } block in build.gradle
EXT_BLOCK_RE = re.compile(r"ext\s*\{([^}]+)\}", re.DOTALL)

# Regex to extract key-value pairs from the ext block
# Handles: extName = 'Value', extVersionCode = 44, isNsfw = true, extNames = ["A", "B"]
KEY_VALUE_RE = re.compile(r"(\w+)\s*=\s*'?([^'\n}]*)'?", re.MULTILINE)

# Regex to extract quoted strings from list literals like ["Jellyfin (1)", "Jellyfin (2)"]
QUOTED_LIST_ITEMS_RE = re.compile(r'"([^"]*)"')

# Regex to find baseUrl in Kotlin source files
KOTLIN_BASE_URL_RE = re.compile(r'override\s+val\s+baseUrl\s*=\s*"([^"]+)"')

# Regex to find BuildConfig.XXX references in Kotlin source files
BUILDCONFIG_REF_RE = re.compile(r"BuildConfig\.(\w+)")

# Regex to detect base64-encoded URLs (must decode to http/https)
BASE64_URL_RE = re.compile(r"^[A-Za-z0-9+/=]{16,}$")

# Regex to find base64-encoded baseUrl in Kotlin source files
# Pattern: val baseUrl = "base64string" or BuildConfig.BASE_URL where BASE_URL is base64
KOTLIN_BASE64_URL_RE = re.compile(
    r'(?:baseUrl|BASE_URL)\s*[=:]\s*"([A-Za-z0-9+/=]{16,})"',
)


def clone_repo(config: Config, target_dir: Path | None = None) -> Path:
    """Shallow-clone the repo and return the path to the cloned directory."""
    dest = target_dir or Path(config.clone_dir)
    if dest.exists():
        # Pull latest if already cloned (for non-CI local usage)
        subprocess.run(
            ["git", "-C", str(dest), "pull", "--ff-only"],
            check=False,
            capture_output=True,
        )
        return dest

    subprocess.run(
        [
            "git", "clone",
            "--depth=1",
            "-b", config.repo_branch,
            config.repo_url,
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    return dest


def get_repo_commit(repo_dir: Path) -> str:
    """Return the short commit hash of the cloned repo."""
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def discover_extensions(repo_dir: Path) -> list[ExtensionMeta]:
    """Walk src/{lang}/{name}/ directories and parse each build.gradle."""
    extensions: list[ExtensionMeta] = []
    src_dir = repo_dir / "src"
    if not src_dir.is_dir():
        return extensions

    for lang_dir in sorted(src_dir.iterdir()):
        if not lang_dir.is_dir():
            continue
        lang = lang_dir.name
        for ext_dir in sorted(lang_dir.iterdir()):
            if not ext_dir.is_dir():
                continue
            build_gradle = ext_dir / "build.gradle"
            build_gradle_kts = ext_dir / "build.gradle.kts"
            gradle_path = (
                build_gradle if build_gradle.is_file()
                else build_gradle_kts if build_gradle_kts.is_file()
                else None
            )
            if gradle_path is None:
                continue

            ext_meta = parse_build_gradle(gradle_path, lang, ext_dir.name, repo_dir)
            if ext_meta is not None:
                # Discover base_url from Kotlin source if not in build.gradle
                if not ext_meta.base_url and not ext_meta.is_multisrc:
                    ext_meta.base_url = discover_base_url_from_kotlin(ext_dir)
                # Check for API key requirements
                ext_meta.requires_api_key = check_api_key_requirement(ext_dir)
                extensions.append(ext_meta)

    return extensions


def parse_build_gradle(
    path: Path,
    lang: str,
    name: str,
    repo_dir: Path | None = None,
) -> ExtensionMeta | None:
    """Parse a build.gradle file and return ExtensionMeta, or None if not parseable."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None
    match = EXT_BLOCK_RE.search(content)
    if not match:
        return None

    block_text = match.group(1)
    raw_kv: dict[str, str] = {}
    for kv_match in KEY_VALUE_RE.finditer(block_text):
        raw_kv[kv_match.group(1)] = kv_match.group(2).strip()

    ext_name = raw_kv.get("extName", "")
    ext_class = raw_kv.get("extClass", "")

    if not ext_name or not ext_class:
        return None

    ext_version_code = int(raw_kv.get("extVersionCode", "0") or "0")
    theme_pkg = raw_kv.get("themePkg") or None
    base_url = raw_kv.get("baseUrl", "")
    override_version_code = int(raw_kv.get("overrideVersionCode", "0") or "0")
    is_nsfw = raw_kv.get("isNsfw", "").lower() in ("true", "1")

    # Extract factory names if present: extNames = ["Jellyfin (1)", "Jellyfin (2)"]
    factory_names: list[str] = []
    if "extNames" in block_text:
        factory_names = QUOTED_LIST_ITEMS_RE.findall(
            block_text[block_text.index("extNames") :],
        )

    return ExtensionMeta(
        lang=lang,
        name=name,
        ext_name=ext_name,
        ext_class=ext_class,
        ext_version_code=ext_version_code,
        theme_pkg=theme_pkg,
        base_url=base_url,
        override_version_code=override_version_code,
        is_nsfw=is_nsfw,
        build_gradle_path=str(path),
        ext_factory_names=factory_names,
    )


def discover_base_url_from_kotlin(ext_dir: Path) -> str:
    """Scan Kotlin source files for override val baseUrl = '...' pattern.

    Also handles base64-encoded baseUrls (e.g. aHR0cHM6Ly9... → https://...).
    """
    src_dir = ext_dir / "src"
    if not src_dir.is_dir():
        return ""

    for kt_file in src_dir.rglob("*.kt"):
        content = kt_file.read_text(encoding="utf-8", errors="replace")
        match = KOTLIN_BASE_URL_RE.search(content)
        if match:
            candidate = match.group(1)
            decoded = try_decode_base64_url(candidate)
            return decoded if decoded else candidate
        match = KOTLIN_BASE64_URL_RE.search(content)
        if match:
            decoded = try_decode_base64_url(match.group(1))
            if decoded:
                return decoded

    return ""


def try_decode_base64_url(value: str) -> str | None:
    """If value looks like base64 and decodes to an http(s) URL, return the decoded URL."""
    if not value or not BASE64_URL_RE.match(value):
        return None
    try:
        decoded = base64.b64decode(value).decode("utf-8", errors="replace")
    except Exception:
        return None
    if decoded.startswith("http://") or decoded.startswith("https://"):
        return decoded
    return None


def check_api_key_requirement(ext_dir: Path, api_key_fields: set[str] | None = None) -> bool:
    """Return True if the extension's source files reference any BuildConfig fields that require API keys."""
    if api_key_fields is None:
        api_key_fields = {"TMDB_API"}

    src_dir = ext_dir / "src"
    if not src_dir.is_dir():
        return False

    for kt_file in src_dir.rglob("*.kt"):
        content = kt_file.read_text(encoding="utf-8", errors="replace")
        for field_name in api_key_fields:
            if f"BuildConfig.{field_name}" in content:
                return True

    return False


def discover_theme_packages(repo_dir: Path) -> list[str]:
    """Dynamically discover all theme packages from lib-multisrc/ directory."""
    multisrc_dir = repo_dir / "lib-multisrc"
    if not multisrc_dir.is_dir():
        return []
    return sorted(
        d.name for d in multisrc_dir.iterdir() if d.is_dir() and (d / "build.gradle.kts").is_file()
    )


def discover_languages(repo_dir: Path) -> list[str]:
    """Dynamically discover all language codes from src/ directory."""
    src_dir = repo_dir / "src"
    if not src_dir.is_dir():
        return []
    return sorted(
        d.name for d in src_dir.iterdir() if d.is_dir() and any(d.iterdir())
    )


def filter_extensions(
    extensions: list[ExtensionMeta],
    config: Config,
) -> list[ExtensionMeta]:
    """Filter extensions based on config.language and config.extensions lists."""
    result = extensions

    if config.languages:
        result = [e for e in result if e.lang in config.languages]

    if config.extensions:
        result = [e for e in result if e.name in config.extensions or e.module_id in config.extensions]

    if config.skip_api_key_extensions:
        result = [e for e in result if not e.requires_api_key]

    return result
