package keiyoushi.testrunner.tests

import keiyoushi.testframework.model.ExtensionMeta
import keiyoushi.testrunner.model.TestResult

/**
 * Abstract base class for all extension test categories.
 * Mirrors Python's ExtensionTest ABC.
 */
abstract class ExtensionTest(
    val config: TestConfig,
) {
    abstract val name: String // e.g. "structural"
    abstract val category: String // e.g. "structural"

    abstract fun run(ext: ExtensionMeta): List<TestResult>

    /**
     * Helper to measure execution time and return Double.
     */
    protected fun measureTime(block: () -> Unit): Double {
        val start = System.currentTimeMillis()
        block()
        return (System.currentTimeMillis() - start).toDouble()
    }

    protected fun result(
        testName: String,
        status: String,
        durationMs: Double = 0.0,
        message: String = "",
        detail: String = "",
    ): TestResult = TestResult(
        testName = "$category:$testName",
        status = status,
        durationMs = durationMs,
        message = message,
        detail = detail,
    )

    protected fun pass(testName: String, durationMs: Double = 0.0, message: String = ""): TestResult = result(testName, TestResult.STATUS_PASS, durationMs, message)

    protected fun fail(testName: String, durationMs: Double = 0.0, message: String = "", detail: String = ""): TestResult = result(testName, TestResult.STATUS_FAIL, durationMs, message, detail)

    protected fun skip(testName: String, durationMs: Double = 0.0, message: String = ""): TestResult = result(testName, TestResult.STATUS_SKIP, durationMs, message)

    protected fun error(testName: String, durationMs: Double = 0.0, message: String = "", detail: String = ""): TestResult = result(testName, TestResult.STATUS_ERROR, durationMs, message, detail)
}
