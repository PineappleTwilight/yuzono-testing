package keiyoushi.testrunner

import keiyoushi.testframework.discovery.ExtensionDiscovery
import keiyoushi.testframework.model.ExtensionMeta
import keiyoushi.testrunner.bootstrap.SourceRunner
import keiyoushi.testrunner.model.ExtensionReport
import keiyoushi.testrunner.model.RunReport
import keiyoushi.testrunner.tests.TestConfig
import keiyoushi.testrunner.tests.TestModule
import java.io.File
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.Semaphore
import java.util.concurrent.TimeUnit

/**
 * Main test runner - orchestrates parallel execution of all test categories.
 * Mirrors Python's runner.py.
 */
object TestRunner {

    /**
     * Run all tests and return the run report.
     */
    fun runAllTests(config: TestConfig): RunReport {
        // Initialize bootstrap
        SourceRunner.setUp()

        // Create report
        val report = RunReport(
            runId = UUID.randomUUID().toString().take(12),
            startedAtMillis = System.currentTimeMillis(),
        )

        // Discover extensions
        val repoDir = File(config.repoDir)
        val allExtensions = ExtensionDiscovery.discover(repoDir)
        val extensions = ExtensionDiscovery.filter(
            extensions = allExtensions,
            languages = config.languages,
            extensionNames = config.extensionNames,
            skipApiKeyExtensions = config.skipApiKeyExtensions,
        )

        // Get test instances
        val testInstances = TestModule.getTests(config)

        // Run tests with bounded concurrency
        val semaphore = Semaphore(config.maxConcurrent)
        val executor = Executors.newFixedThreadPool(config.maxConcurrent)

        val extReports = mutableListOf<ExtensionReport>()

        for (ext in extensions) {
            semaphore.acquire()
            val future = executor.submit<ExtensionReport> {
                try {
                    runExtensionTests(ext, testInstances, config)
                } finally {
                    semaphore.release()
                }
            }
            extReports.add(future.get(config.httpTotalTimeout.toLong(), TimeUnit.SECONDS))
        }

        executor.shutdown()
        executor.awaitTermination(1, TimeUnit.HOURS)

        return report.copy(
            finishedAtMillis = System.currentTimeMillis(),
            extensions = extReports,
        )
    }

    private fun runExtensionTests(
        ext: ExtensionMeta,
        testInstances: List<keiyoushi.testrunner.tests.ExtensionTest>,
        config: TestConfig,
    ): ExtensionReport {
        val startedAtMillis = System.currentTimeMillis()
        val results = mutableListOf<keiyoushi.testrunner.model.TestResult>()

        for (testInstance in testInstances) {
            try {
                val testResults = testInstance.run(ext)
                results.addAll(testResults)
            } catch (e: Exception) {
                results.add(
                    keiyoushi.testrunner.model.TestResult(
                        testName = "${testInstance.category}:unexpected_error",
                        status = keiyoushi.testrunner.model.TestResult.STATUS_ERROR,
                        message = "Unexpected error: ${e.message}",
                    ),
                )
            }
        }

        return ExtensionReport(
            extension = ext,
            results = results,
            startedAtMillis = startedAtMillis,
            finishedAtMillis = System.currentTimeMillis(),
        )
    }

    /**
     * Run tests for a specific extension (useful for debugging).
     */
    fun runExtension(ext: ExtensionMeta, config: TestConfig): ExtensionReport {
        SourceRunner.setUp()
        val testInstances = TestModule.getTests(config)
        return runExtensionTests(ext, testInstances, config)
    }
}
