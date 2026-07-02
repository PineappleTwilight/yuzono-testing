package keiyoushi.testrunner.model

/**
 * Summary statistics for a test run.
 * Mirrors Python's RunSummary dataclass.
 */
data class RunSummary(
    val totalExtensions: Int,
    val totalPassed: Int,
    val totalFailed: Int,
    val totalSkipped: Int,
    val totalErrored: Int,
    val byLanguage: Map<String, LanguageStats>,
    val byCategory: Map<String, CategoryStats>,
)

data class LanguageStats(
    val lang: String,
    val total: Int,
    val passed: Int,
    val failed: Int,
    val skipped: Int,
    val errored: Int,
)

data class CategoryStats(
    val category: String,
    val total: Int,
    val passed: Int,
    val failed: Int,
    val skipped: Int,
    val errored: Int,
)
