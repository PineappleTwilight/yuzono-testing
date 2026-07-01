# Anime Extensions Testing

Automated live HTTP testing suite for [yuzono/anime-extensions](https://github.com/yuzono/anime-extensions). Tests 259+ extensions across 17 languages by exercising their actual HTTP API contracts — fetching popular lists, searching, loading details, retrieving episode lists, and verifying video stream endpoints.

## Features

- **13 test categories** covering structural validation, connectivity, search, details, episodes, filters, pagination, series details, episode lists, video streams, and more
- **Live HTTP testing** — real requests against extension servers, not just static analysis
- **11 theme patterns** with 18+ fields each, modeling each multisrc theme's unique URL structure and XHR endpoints
- **Parallel execution** — configurable concurrency with bounded semaphores
- **Multi-format reports** — JSON, Markdown, and self-contained interactive HTML
- **GitHub Actions CI** — weekly scheduled runs, manual triggers, PR integration, and GitHub Pages deployment
- **PR comments** — automated test result summaries posted directly on pull requests

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run all tests (clones repo, tests every extension)
python -m anime_ext_test -vv

# Run with all report formats (JSON + Markdown + HTML)
python -m anime_ext_test --format all -vv

# Test only Turkish extensions
python -m anime_ext_test --languages tr -vv

# Test a specific extension
python -m anime_ext_test --extensions animepahe -vv

# Use a local checkout instead of cloning
python -m anime_ext_test --no-clone --repo-dir ./anime-extensions -vv

# Run specific test categories
python -m anime_ext_test --categories structural connectivity popular -vv
```

## CLI Options

### Repository

| Flag | Default | Description |
|------|---------|-------------|
| `--repo-url` | `https://github.com/yuzono/anime-extensions.git` | Git repo to clone |
| `--repo-branch` | `master` | Branch to clone |
| `--no-clone` | off | Skip cloning, use `--repo-dir` |
| `--repo-dir` | `repo/` | Local repo path or clone target |

### Filtering

| Flag | Default | Description |
|------|---------|-------------|
| `--languages` | all | Space-separated language codes (e.g. `en ja tr`) |
| `--extensions` | all | Space-separated extension names or module IDs |
| `--categories` | all 13 | Space-separated test categories to run |

### HTTP

| Flag | Default | Description |
|------|---------|-------------|
| `--timeout` | 30.0 | Per-request timeout (seconds) |
| `--connect-timeout` | 15.0 | Connect timeout (seconds) |
| `--max-concurrent` | 20 | Max parallel HTTP requests |

### Output

| Flag | Default | Description |
|------|---------|-------------|
| `--output-dir` | `./reports` | Directory for report files |
| `--format` | `both` | `json`, `markdown`, `html`, `both` (json+markdown), `all` (json+markdown+html) |
| `--include-api-key` | off | Include extensions requiring API keys (skipped by default) |
| `-v` / `-vv` | warning | Increase log verbosity |

## Test Categories

| Category | What It Tests |
|----------|---------------|
| `structural` | Build.gradle fields, class naming, manifest consistency, base URL presence |
| `connectivity` | Base URL reachability, HTTP status codes, redirect handling |
| `popular` | Popular/latest anime list endpoint returns valid data |
| `search` | Search endpoint returns results for common queries |
| `latest` | Latest updates endpoint works |
| `details` | Series detail pages load with expected fields (title, description, artwork) |
| `episodes` | Episode count is available and > 0 |
| `filters` | Filter/category system is accessible |
| `series_details` | Deep series metadata validation |
| `episode_list` | Full episode list retrieval with episode numbers |
| `video_streams` | Video stream URLs are resolvable |
| `pagination` | Paginated endpoints return next-page data |
| `post_search` | POST-based search endpoints (4 themes use POST) |

## Architecture

```
src/anime_ext_test/
├── cli.py              CLI entry point & argument parsing
├── config.py           Immutable Config dataclass
├── models.py           Pydantic models (ExtensionMeta, TestResult, ExtensionReport, RunReport, RunSummary)
├── discovery.py        Repo cloning, build.gradle parsing, base URL extraction (including base64)
├── http_client.py      Async HTTP session factory (aiohttp), fetch_html, fetch_with_headers, fetch_json
├── theme_patterns.py   11 theme definitions with 18+ fields each
├── runner.py           Parallel test orchestrator with bounded concurrency
├── tests/
│   ├── registry.py     Test class registry & get_all_tests()
│   ├── structural.py   10 structural checks
│   ├── connectivity.py 5 connectivity checks
│   ├── popular.py      Popular list fetching
│   ├── search.py       Search endpoint testing
│   ├── latest.py       Latest updates
│   ├── details.py      Series detail pages
│   ├── episodes.py     Episode count verification
│   ├── filters.py      Filter system testing
│   ├── series_details.py  Deep series metadata
│   ├── episode_list.py   Full episode listing
│   ├── video_streams.py  Video stream URL resolution
│   ├── pagination.py     Paginated endpoint testing
│   └── post_search.py    POST-based search
└── report/
    ├── json_report.py    JSON + summary JSON output
    ├── markdown_report.py Markdown report
    ├── html_report.py    Self-contained interactive HTML report
    └── summary.py         Summary computation
```

### How It Works

1. **Discovery** — Clones the anime-extensions repo, walks `src/{lang}/` directories, parses each extension's `build.gradle` to extract metadata (extName, extClass, theme package, base URL, NSFW flag, API key requirements). Base URLs encoded as base64 are decoded automatically.

2. **Theme Pattern Matching** — Each multisrc extension is matched to one of 11 theme patterns. Each pattern defines 18+ fields describing URL templates for popular, search, details, episodes, and stream endpoints, plus XHR paths and POST data formats.

3. **Parallel Execution** — Extensions are tested concurrently with a configurable semaphore (default: 20). Each extension gets its own timeout budget. Structural tests run locally; all other tests make live HTTP requests.

4. **Report Generation** — Results are aggregated into a `RunReport` containing `ExtensionReport` objects, each with a list of `TestResult` entries. Reports are written in JSON, Markdown, and/or interactive HTML.

## HTML Report

The HTML report is a fully self-contained page (no external CSS/JS dependencies) with:

- Dark-themed dashboard with summary cards
- Category and language breakdown tables
- Collapsible extension cards with per-test result rows
- Search filtering and quick-filter buttons (All / Failed / Clean)
- Toggle to show/hide passing tests (hidden by default to focus on failures)
- Health indicator dots and percentage per extension

Open `reports/report-{run_id}.html` in any browser.

## GitHub Actions

The CI workflow (`.github/workflows/test-extensions.yml`) provides:

| Trigger | Behavior |
|---------|----------|
| **Weekly** (Monday 00:00 UTC) | Full test run across all extensions |
| **Manual `workflow_dispatch`** | Configurable languages, categories, concurrency |
| **Pull request** | Tests changes to `src/`, `tests/`, `pyproject.toml`, `requirements.txt`, or the workflow itself |

### CI Pipeline

1. **detect-languages** — Clones the repo, groups languages by size (en/es/pt/all individually; medium languages batched; small languages batched)
2. **test-extensions** — Matrix strategy runs each language group in parallel, generates JSON/Markdown/HTML reports
3. **aggregate-reports** — Downloads all group artifacts, merges into a single RunReport, generates all three report formats
4. **deploy-pages** — Deploys merged reports to GitHub Pages
5. **PR comment** — Posts a summary table on the PR with pass/fail counts

### Setting Up CI

1. Push this project to a GitHub repository
2. Go to **Settings → Pages → Source** and select "GitHub Actions" as the deployment source
3. The workflow will run automatically on the schedule, or you can trigger it manually from the Actions tab

Report artifacts are retained for 30 days. The merged HTML report is deployed to GitHub Pages for easy browser access.

## Development

```bash
# Install with dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov ruff

# Run unit tests
pytest

# Lint
ruff check src/ tests/

# Run integration test (Turkish, all categories, verbose)
python -m anime_ext_test --languages tr --format all -vv
```

## Extension Stats

- **259** extensions across **17** languages
- **11** multisrc themes (dopeflix, kemtilde, etc.)
- **6** themes deliver episodes via XHR/AJAX endpoints
- **4** themes use POST-based search
- Extensions requiring API keys are skipped by default (use `--include-api-key` to include them)

## License

This testing suite is provided as-is for validating the anime-extensions project.
