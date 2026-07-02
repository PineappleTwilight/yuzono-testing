package keiyoushi.testframework.discovery

import keiyoushi.testframework.model.ExtensionMeta
import java.io.File
import java.util.Base64

/**
 * Parses Android application [build.gradle] / [build.gradle.kts] files to extract
 * extension metadata from the `ext { ... }` block.
 *
 * Handles:
 * - Simple key=value pairs: `extName = 'AnimePahe'`
 * - Integer values: `extVersionCode = 44`
 * - Boolean values: `isNsfw = true`
 * - List literals: `extNames = ["Jellyfin (1)", "Jellyfin (2)"]`
 */
object BuildGradleParser {

    private val EXT_BLOCK_RE = Regex("""ext\s*\{([^}]+)""", RegexOption.DOT_MATCHES_ALL)
    private val KEY_VALUE_RE = Regex("""(\w+)\s*=\s*'?([^'\n}]*)'?""")
    private val QUOTED_LIST_ITEMS_RE = Regex(""""([^"]*)"""")
    private val KOTLIN_BASE_URL_RE = Regex("""override\s+val\s+baseUrl\s*=\s*"([^"]+)"""")
    private val KOTLIN_BASE64_URL_RE = Regex("""(?:baseUrl|BASE_URL)\s*[=:]\s*"([A-Za-z0-9+/=]{16,})"""")
    private val BASE64_URL_RE = Regex("""^[A-Za-z0-9+/=]{16,}$""")

    /**
     * Parse the given build.gradle file and return an [ExtensionMeta],
     * or null if the file doesn't contain a valid `ext { ... }` block.
     *
     * @param file the build.gradle or build.gradle.kts file
     * @param lang language code from the parent directory
     * @param name extension directory name
     * @param extDir the extension's root directory (for baseUrl scanning)
     */
    fun parse(file: File, lang: String, name: String, extDir: File): ExtensionMeta? {
        val content = file.readText(Charsets.UTF_8)
        val blockMatch = EXT_BLOCK_RE.find(content) ?: return null
        val blockText = blockMatch.groupValues[1]

        val rawKv = mutableMapOf<String, String>()
        for (kvMatch in KEY_VALUE_RE.findAll(blockText)) {
            rawKv[kvMatch.groupValues[1]] = kvMatch.groupValues[2].trim()
        }

        val extName = rawKv["extName"] ?: ""
        val extClass = rawKv["extClass"] ?: ""
        if (extName.isBlank() || extClass.isBlank()) return null

        val extVersionCode = rawKv["extVersionCode"]?.toIntOrNull() ?: 0
        val themePkg = rawKv["themePkg"]
        var baseUrl = rawKv["baseUrl"] ?: ""
        val overrideVersionCode = rawKv["overrideVersionCode"]?.toIntOrNull() ?: 0
        val isNsfw = rawKv["isNsfw"]?.lowercase() in listOf("true", "1")

        // Extract factory names if present
        val factoryNames = if ("extNames" in blockText) {
            val suffix = blockText.substringAfter("extNames")
            QUOTED_LIST_ITEMS_RE.findAll(suffix).map { it.groupValues[1] }.toList()
        } else {
            emptyList()
        }

        // If baseUrl not in build.gradle and not multisrc, scan Kotlin sources
        if (baseUrl.isBlank() && themePkg == null) {
            baseUrl = discoverBaseUrlFromKotlin(extDir)
        }

        val requiresApiKey = checkApiKeyRequirement(extDir)

        return ExtensionMeta(
            lang = lang,
            name = name,
            extName = extName,
            extClass = extClass,
            extVersionCode = extVersionCode,
            themePkg = themePkg,
            baseUrl = baseUrl,
            overrideVersionCode = overrideVersionCode,
            isNsfw = isNsfw,
            requiresApiKey = requiresApiKey,
            buildGradlePath = file.absolutePath,
            extFactoryNames = factoryNames,
        )
    }

    /**
     * Scan Kotlin source files for `override val baseUrl = "..."` pattern.
     * Also handles base64-encoded baseUrls.
     */
    private fun discoverBaseUrlFromKotlin(extDir: File): String {
        val srcDir = File(extDir, "src")
        if (!srcDir.isDirectory) return ""

        val ktFiles = srcDir.walkTopDown().filter { it.extension == "kt" }
        for (ktFile in ktFiles) {
            val content = ktFile.readText(Charsets.UTF_8)
            val plainMatch = KOTLIN_BASE_URL_RE.find(content)
            if (plainMatch != null) {
                val candidate = plainMatch.groupValues[1]
                return tryDecodeBase64Url(candidate) ?: candidate
            }
            val b64Match = KOTLIN_BASE64_URL_RE.find(content)
            if (b64Match != null) {
                val decoded = tryDecodeBase64Url(b64Match.groupValues[1])
                if (decoded != null) return decoded
            }
        }
        return ""
    }

    /**
     * If the value looks like base64 and decodes to an http(s) URL, return the decoded URL.
     */
    private fun tryDecodeBase64Url(value: String): String? {
        if (value.isBlank() || !BASE64_URL_RE.matches(value)) return null
        return try {
            val decoded = String(Base64.getDecoder().decode(value), Charsets.UTF_8)
            if (decoded.startsWith("http://") || decoded.startsWith("https://")) decoded else null
        } catch (_: Exception) {
            null
        }
    }

    /**
     * Return true if the extension's source files reference any BuildConfig fields
     * that require API keys.
     */
    private fun checkApiKeyRequirement(extDir: File, apiKeyFields: Set<String> = setOf("TMDB_API")): Boolean {
        val srcDir = File(extDir, "src")
        if (!srcDir.isDirectory) return false

        val ktFiles = srcDir.walkTopDown().filter { it.extension == "kt" }
        for (ktFile in ktFiles) {
            val content = ktFile.readText(Charsets.UTF_8)
            for (fieldName in apiKeyFields) {
                if ("BuildConfig.$fieldName" in content) return true
            }
        }
        return false
    }
}
