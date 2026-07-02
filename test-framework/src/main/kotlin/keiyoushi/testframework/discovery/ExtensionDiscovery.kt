package keiyoushi.testframework.discovery

import keiyoushi.testframework.model.ExtensionMeta
import java.io.File

/**
 * Discovers extensions by walking the `src/{lang}/{name}/` directory tree
 * inside the cloned anime-extensions repo.
 *
 * For each extension directory, finds the build.gradle(.kts), parses its
 * `ext { ... }` block for metadata, and optionally scans Kotlin source
 * files for baseUrl and API key requirements.
 */
object ExtensionDiscovery {

    /**
     * Walk `src/{lang}/` directories in [repoDir] and return a list of
     * [ExtensionMeta] for every valid extension found.
     */
    fun discover(repoDir: File): List<ExtensionMeta> {
        val srcDir = File(repoDir, "src")
        if (!srcDir.isDirectory) return emptyList()

        val extensions = mutableListOf<ExtensionMeta>()

        val langDirs = srcDir.listFiles()?.filter { it.isDirectory }?.sortedBy { it.name } ?: return emptyList()
        for (langDir in langDirs) {
            val lang = langDir.name
            val extDirs = langDir.listFiles()?.filter { it.isDirectory }?.sortedBy { it.name } ?: continue
            for (extDir in extDirs) {
                val gradleFile = findBuildGradle(extDir) ?: continue
                val meta = BuildGradleParser.parse(gradleFile, lang, extDir.name, extDir)
                if (meta != null) {
                    extensions.add(meta)
                }
            }
        }

        return extensions
    }

    /**
     * Discover all language codes present in the repo's `src/` directory.
     */
    fun discoverLanguages(repoDir: File): List<String> {
        val srcDir = File(repoDir, "src")
        if (!srcDir.isDirectory) return emptyList()
        return srcDir.listFiles()
            ?.filter { it.isDirectory && it.listFiles()?.isNotEmpty() == true }
            ?.map { it.name }
            ?.sorted()
            ?: emptyList()
    }

    /**
     * Discover all theme packages from the `lib-multisrc/` directory.
     */
    fun discoverThemePackages(repoDir: File): List<String> {
        val multisrcDir = File(repoDir, "lib-multisrc")
        if (!multisrcDir.isDirectory) return emptyList()
        return multisrcDir.listFiles()
            ?.filter { it.isDirectory && File(it, "build.gradle.kts").isFile }
            ?.map { it.name }
            ?.sorted()
            ?: emptyList()
    }

    /**
     * Filter [extensions] by language codes and/or extension names.
     * If [languages] is empty, all languages are included.
     * If [extensionNames] is empty, all extensions are included.
     * If [skipApiKeyExtensions] is true, extensions requiring API keys are excluded.
     */
    fun filter(
        extensions: List<ExtensionMeta>,
        languages: Set<String> = emptySet(),
        extensionNames: Set<String> = emptySet(),
        skipApiKeyExtensions: Boolean = true,
    ): List<ExtensionMeta> {
        var result = extensions
        if (languages.isNotEmpty()) {
            result = result.filter { it.lang in languages }
        }
        if (extensionNames.isNotEmpty()) {
            result = result.filter { it.name in extensionNames || it.moduleId in extensionNames }
        }
        if (skipApiKeyExtensions) {
            result = result.filter { !it.requiresApiKey }
        }
        return result
    }

    private fun findBuildGradle(extDir: File): File? {
        val groovy = File(extDir, "build.gradle")
        if (groovy.isFile) return groovy
        val kts = File(extDir, "build.gradle.kts")
        if (kts.isFile) return kts
        return null
    }
}
