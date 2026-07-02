package keiyoushi.testrunner.model

import kotlinx.serialization.Serializable

/**
 * A single test check result.
 * Mirrors Python's TestResult dataclass.
 */
@Serializable
data class TestResult(
    val testName: String, // "{category}:{check_name}" e.g. "popular:popular_page_load"
    val status: String, // "pass" | "fail" | "skip" | "error"
    val durationMs: Double = 0.0,
    val message: String = "",
    val detail: String = "",
) {
    companion object {
        const val STATUS_PASS = "pass"
        const val STATUS_FAIL = "fail"
        const val STATUS_SKIP = "skip"
        const val STATUS_ERROR = "error"
    }
}
