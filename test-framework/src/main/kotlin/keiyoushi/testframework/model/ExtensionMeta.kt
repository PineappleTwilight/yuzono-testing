package keiyoushi.testframework.model

/**
 * Metadata for a single extension, parsed from its build.gradle.
 * Mirrors the Python `ExtensionMeta` dataclass.
 */
data class ExtensionMeta(
    /** Language code, e.g. "en" */
    val lang: String,
    /** Directory name, e.g. "animepahe" */
    val name: String,
    /** extName from build.gradle, e.g. "AnimePahe" */
    val extName: String,
    /** extClass from build.gradle, e.g. ".AnimePahe" */
    val extClass: String,
    val extVersionCode: Int = 0,
    /** Theme package for multisrc extensions, e.g. "dopeflix", or null for legacy */
    val themePkg: String? = null,
    val baseUrl: String = "",
    val overrideVersionCode: Int = 0,
    val isNsfw: Boolean = false,
    val requiresApiKey: Boolean = false,
    val buildGradlePath: String = "",
    /** For factory sources: extNames = ["Jellyfin (1)", "Jellyfin (2)"] */
    val extFactoryNames: List<String> = emptyList(),
) {
    /** Class name without leading dot, used for file resolution */
    val classSimpleName: String get() = extClass.trimStart('.')

    /** Module ID in the form "lang.name", e.g. "en.animepahe" */
    val moduleId: String get() = "$lang.$name"

    /** Whether this is a multisrc extension (has a themePkg) */
    val isMultisrc: Boolean get() = themePkg != null
}
