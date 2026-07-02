package keiyoushi.testrunner.model

import java.util.UUID

/**
 * Complete test run report.
 * Mirrors Python's RunReport dataclass.
 */
data class RunReport(
    val runId: String = UUID.randomUUID().toString().take(12),
    val startedAtMillis: Long = System.currentTimeMillis(),
    val finishedAtMillis: Long? = null,
    val repoUrl: String = "",
    val repoCommit: String? = null,
    val extensions: List<ExtensionReport> = emptyList(),
) {
    val totalPassed: Int get() = extensions.sumOf { it.passed }
    val totalFailed: Int get() = extensions.sumOf { it.failed }
    val totalSkipped: Int get() = extensions.sumOf { it.skipped }
    val totalErrored: Int get() = extensions.sumOf { it.errored }
    val totalTests: Int get() = extensions.sumOf { it.total }

    val durationSeconds: Double get() {
        val end = finishedAtMillis ?: System.currentTimeMillis()
        return (end - startedAtMillis).toDouble() / 1000.0
    }

    val overallPassRate: Double get() = if (totalTests > 0) {
        totalPassed.toDouble() / totalTests
    } else {
        0.0
    }

    fun getSummary(): RunSummary {
        val byLanguage = extensions
            .groupBy { it.extension.lang }
            .mapValues { (lang, reports) ->
                LanguageStats(
                    lang = lang,
                    total = reports.sumOf { it.total },
                    passed = reports.sumOf { it.passed },
                    failed = reports.sumOf { it.failed },
                    skipped = reports.sumOf { it.skipped },
                    errored = reports.sumOf { it.errored },
                )
            }

        val byCategory = extensions
            .flatMap { it.results }
            .groupBy { it.testName.substringBefore(":") }
            .mapValues { (category, results) ->
                CategoryStats(
                    category = category,
                    total = results.size,
                    passed = results.count { it.status == TestResult.STATUS_PASS },
                    failed = results.count { it.status == TestResult.STATUS_FAIL },
                    skipped = results.count { it.status == TestResult.STATUS_SKIP },
                    errored = results.count { it.status == TestResult.STATUS_ERROR },
                )
            }

        return RunSummary(
            totalExtensions = extensions.size,
            totalPassed = totalPassed,
            totalFailed = totalFailed,
            totalSkipped = totalSkipped,
            totalErrored = totalErrored,
            byLanguage = byLanguage,
            byCategory = byCategory,
        )
    }
}
