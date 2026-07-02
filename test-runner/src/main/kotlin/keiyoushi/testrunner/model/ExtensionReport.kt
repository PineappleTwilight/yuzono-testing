package keiyoushi.testrunner.model

import keiyoushi.testframework.model.ExtensionMeta

/**
 * Results for a single extension.
 * Mirrors Python's ExtensionReport dataclass.
 */
data class ExtensionReport(
    val extension: ExtensionMeta,
    val results: List<TestResult> = emptyList(),
    val startedAtMillis: Long? = null,
    val finishedAtMillis: Long? = null,
) {
    val passed: Int get() = results.count { it.status == TestResult.STATUS_PASS }
    val failed: Int get() = results.count { it.status == TestResult.STATUS_FAIL }
    val skipped: Int get() = results.count { it.status == TestResult.STATUS_SKIP }
    val errored: Int get() = results.count { it.status == TestResult.STATUS_ERROR }

    val total: Int get() = results.size

    val passRate: Double get() = if (total > 0) passed.toDouble() / total else 0.0

    val moduleId: String get() = extension.moduleId
}
