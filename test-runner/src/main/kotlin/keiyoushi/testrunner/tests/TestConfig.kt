package keiyoushi.testrunner.tests

/**
 * Configuration for test execution.
 * Mirrors Python's Config dataclass.
 */
data class TestConfig(
    val repoDir: String = "repo/",
    val languages: Set<String> = emptySet(),
    val extensionNames: Set<String> = emptySet(),
    val testCategories: Set<String> = emptySet(),
    val timeout: Double = 30.0,
    val connectTimeout: Double = 15.0,
    val maxConcurrent: Int = 20,
    val httpTotalTimeout: Double = 120.0,
    val skipApiKeyExtensions: Boolean = true,
    val includeApiKeyExtensions: Boolean = false,
    val outputDir: String = "./reports",
    val format: ReportFormat = ReportFormat.BOTH,
)

enum class ReportFormat(val value: String) {
    JSON("json"),
    MARKDOWN("markdown"),
    HTML("html"),
    BOTH("both"),
    ALL("all"),
    ;

    companion object {
        fun fromString(value: String): ReportFormat = entries.find { it.value == value.lowercase() } ?: BOTH
    }
}
