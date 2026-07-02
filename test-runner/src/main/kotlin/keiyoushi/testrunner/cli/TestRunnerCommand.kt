package keiyoushi.testrunner.cli

import keiyoushi.testrunner.TestRunner
import keiyoushi.testrunner.report.ReportGenerator
import keiyoushi.testrunner.tests.ReportFormat
import keiyoushi.testrunner.tests.TestConfig
import java.io.File

/**
 * Simple CLI entry point for the test runner.
 * Uses basic argument parsing instead of clikt.
 */
object TestRunnerCLI {

    fun main(args: Array<String>) {
        var repoDir = "repo/"
        var languages = emptySet<String>()
        var extensions = emptySet<String>()
        var categories = emptySet<String>()
        var timeout = 30.0
        var maxConcurrent = 20
        var outputDir = "./reports"
        var format = "both"
        var includeApiKey = false

        var i = 0
        while (i < args.size) {
            when (args[i]) {
                "--repo-dir" -> {
                    repoDir = args[++i]
                }
                "--languages" -> {
                    languages = args[++i].split(" ").toSet()
                }
                "--extensions" -> {
                    extensions = args[++i].split(" ").toSet()
                }
                "--categories" -> {
                    categories = args[++i].split(" ").toSet()
                }
                "--timeout" -> {
                    timeout = args[++i].toDouble()
                }
                "--max-concurrent" -> {
                    maxConcurrent = args[++i].toInt()
                }
                "--output-dir" -> {
                    outputDir = args[++i]
                }
                "--format" -> {
                    format = args[++i]
                }
                "--include-api-key" -> {
                    includeApiKey = true
                }
                else -> {
                    if (args[i].startsWith("-")) {
                        println("Unknown option: ${args[i]}")
                        printUsage()
                        return
                    }
                }
            }
            i++
        }

        val config = TestConfig(
            repoDir = repoDir,
            languages = languages,
            extensionNames = extensions,
            testCategories = categories,
            timeout = timeout,
            connectTimeout = timeout * 0.5,
            maxConcurrent = maxConcurrent,
            httpTotalTimeout = timeout * 4,
            skipApiKeyExtensions = !includeApiKey,
            includeApiKeyExtensions = includeApiKey,
            outputDir = outputDir,
            format = ReportFormat.fromString(format),
        )

        File(outputDir).mkdirs()

        println("Running extension tests...")
        val report = TestRunner.runAllTests(config)

        println("Generating reports...")
        val reportFormat = ReportFormat.fromString(format)
        ReportGenerator.generate(report, outputDir, reportFormat)

        println("")
        println("=== Test Run Summary ===")
        println("Run ID: ${report.runId}")
        println("Extensions: ${report.extensions.size}")
        println("Passed: ${report.totalPassed}")
        println("Failed: ${report.totalFailed}")
        println("Skipped: ${report.totalSkipped}")
        println("Errored: ${report.totalErrored}")
        println("Duration: ${report.durationSeconds}s")
        println("")
        println("Reports saved to: $outputDir")
    }

    private fun printUsage() {
        println(
            """
Usage: anime-ext-test [options]
Options:
  --repo-dir <path>          Local repo path (default: repo/)
  --languages <codes>        Space-separated language codes (e.g. en ja tr)
  --extensions <names>      Space-separated extension names
  --categories <cats>        Space-separated test categories
  --timeout <seconds>       Per-request timeout (default: 30.0)
  --max-concurrent <n>      Max parallel requests (default: 20)
  --output-dir <path>       Output directory (default: ./reports)
  --format <format>         Report format: json, markdown, html, both, all
  --include-api-key          Include extensions requiring API keys
            """.trimIndent(),
        )
    }
}

fun main(args: Array<String>) {
    TestRunnerCLI.main(args)
}
