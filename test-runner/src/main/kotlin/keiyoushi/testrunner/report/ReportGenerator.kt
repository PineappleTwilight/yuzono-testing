package keiyoushi.testrunner.report

import keiyoushi.testrunner.model.RunReport
import keiyoushi.testrunner.model.RunSummary
import keiyoushi.testrunner.tests.ReportFormat
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.File

/**
 * Report generator - creates JSON, Markdown, and HTML reports.
 * Mirrors Python's report/ module.
 */
object ReportGenerator {

    private val json = Json {
        prettyPrint = true
        encodeDefaults = true
    }

    fun generate(report: RunReport, outputDir: String, format: ReportFormat) {
        val summary = report.getSummary()

        when (format) {
            ReportFormat.JSON -> generateJson(report, outputDir)
            ReportFormat.MARKDOWN -> generateMarkdown(report, summary, outputDir)
            ReportFormat.HTML -> generateHtml(report, summary, outputDir)
            ReportFormat.BOTH -> {
                generateJson(report, outputDir)
                generateMarkdown(report, summary, outputDir)
            }
            ReportFormat.ALL -> {
                generateJson(report, outputDir)
                generateMarkdown(report, summary, outputDir)
                generateHtml(report, summary, outputDir)
            }
        }
    }

    private fun generateJson(report: RunReport, outputDir: String) {
        val jsonReport = json.encodeToString(report)
        val file = File(outputDir, "report-${report.runId}.json")
        file.writeText(jsonReport)
    }

    private fun generateMarkdown(report: RunReport, summary: RunSummary, outputDir: String) {
        val sb = StringBuilder()

        sb.appendLine("# Extension Test Report")
        sb.appendLine()
        sb.appendLine("**Run ID:** `${report.runId}`")
        sb.appendLine("**Started:** ${report.startedAtMillis}")
        sb.appendLine("**Duration:** ${report.durationSeconds}s")
        sb.appendLine()
        sb.appendLine("## Summary")
        sb.appendLine()
        sb.appendLine("| Metric | Count |")
        sb.appendLine("|--------|-------|")
        sb.appendLine("| Extensions | ${summary.totalExtensions} |")
        sb.appendLine("| Passed | ${summary.totalPassed} |")
        sb.appendLine("| Failed | ${summary.totalFailed} |")
        sb.appendLine("| Skipped | ${summary.totalSkipped} |")
        sb.appendLine("| Errored | ${summary.totalErrored} |")
        sb.appendLine()

        sb.appendLine("## By Language")
        sb.appendLine()
        sb.appendLine("| Language | Total | Pass | Fail | Skip | Error |")
        sb.appendLine("|----------|-------|------|------|------|-------|")
        for ((lang, stats) in summary.byLanguage.entries.sortedBy { it.key }) {
            sb.appendLine("| $lang | ${stats.total} | ${stats.passed} | ${stats.failed} | ${stats.skipped} | ${stats.errored} |")
        }
        sb.appendLine()

        sb.appendLine("## By Category")
        sb.appendLine()
        sb.appendLine("| Category | Total | Pass | Fail | Skip | Error |")
        sb.appendLine("|----------|-------|------|------|------|-------|")
        for ((cat, stats) in summary.byCategory.entries.sortedBy { it.key }) {
            sb.appendLine("| $cat | ${stats.total} | ${stats.passed} | ${stats.failed} | ${stats.skipped} | ${stats.errored} |")
        }
        sb.appendLine()

        // Extension details
        sb.appendLine("## Extension Details")
        sb.appendLine()
        for (extReport in report.extensions.sortedBy { it.moduleId }) {
            sb.appendLine("### ${extReport.moduleId}")
            sb.appendLine()
            sb.appendLine("| Test | Status | Duration | Message |")
            sb.appendLine("|------|--------|----------|---------|")
            for (result in extReport.results) {
                val status = result.status.uppercase()
                val message = result.message.take(50).replace("|", "\\|")
                sb.appendLine("| ${result.testName} | $status | ${result.durationMs}ms | $message |")
            }
            sb.appendLine()
        }

        val file = File(outputDir, "report-${report.runId}.md")
        file.writeText(sb.toString())
    }

    private fun generateHtml(report: RunReport, summary: RunSummary, outputDir: String) {
        val sb = StringBuilder()

        sb.appendLine(
            """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Extension Test Report - ${report.runId}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f1a; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1, h2, h3 { color: #fff; margin-bottom: 1rem; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .card { background: #1a1a2e; padding: 1.5rem; border-radius: 8px; text-align: center; }
        .card .value { font-size: 2rem; font-weight: bold; }
        .card .label { color: #888; margin-top: 0.5rem; }
        .card.passed .value { color: #4caf50; }
        .card.failed .value { color: #f44336; }
        .card.skipped .value { color: #ff9800; }
        .card.errored .value { color: #9c27b0; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #333; }
        th { background: #1a1a2e; color: #fff; }
        tr:hover { background: #1a1a2e; }
        .status { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; }
        .status.pass { background: #4caf50; color: #fff; }
        .status.fail { background: #f44336; color: #fff; }
        .status.skip { background: #ff9800; color: #fff; }
        .status.error { background: #9c27b0; color: #fff; }
        .ext-card { background: #1a1a2e; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
        .ext-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
        .ext-name { font-weight: bold; font-size: 1.1rem; }
        .ext-stats { color: #888; font-size: 0.9rem; }
        .ext-details { display: none; margin-top: 1rem; }
        .ext-details.open { display: block; }
        .search-box { width: 100%; padding: 0.75rem; background: #1a1a2e; border: 1px solid #333; border-radius: 8px; color: #fff; margin-bottom: 1rem; }
        .filters { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
        .filter-btn { padding: 0.5rem 1rem; background: #1a1a2e; border: 1px solid #333; border-radius: 4px; color: #fff; cursor: pointer; }
        .filter-btn.active { background: #4caf50; border-color: #4caf50; }
    </style>
</head>
<body>
<div class="container">
    <h1>Extension Test Report</h1>
    <p>Run ID: <code>${report.runId}</code> | Started: ${report.startedAtMillis} | Duration: ${String.format("%.1f", report.durationSeconds)}s</p>
""",
        )

        // Summary cards
        sb.appendLine("    <div class=\"summary\">")
        sb.appendLine("""        <div class="card passed"><div class="value">${summary.totalPassed}</div><div class="label">Passed</div></div>""")
        sb.appendLine("""        <div class="card failed"><div class="value">${summary.totalFailed}</div><div class="label">Failed</div></div>""")
        sb.appendLine("""        <div class="card skipped"><div class="value">${summary.totalSkipped}</div><div class="label">Skipped</div></div>""")
        sb.appendLine("""        <div class="card errored"><div class="value">${summary.totalErrored}</div><div class="label">Errored</div></div>""")
        sb.appendLine("    </div>")

        // Language breakdown
        sb.appendLine("    <h2>By Language</h2>")
        sb.appendLine("    <table>")
        sb.appendLine("        <tr><th>Language</th><th>Total</th><th>Pass</th><th>Fail</th><th>Skip</th><th>Error</th></tr>")
        for ((lang, stats) in summary.byLanguage.entries.sortedBy { it.key }) {
            sb.appendLine("        <tr><td>$lang</td><td>${stats.total}</td><td>${stats.passed}</td><td>${stats.failed}</td><td>${stats.skipped}</td><td>${stats.errored}</td></tr>")
        }
        sb.appendLine("    </table>")

        // Category breakdown
        sb.appendLine("    <h2>By Category</h2>")
        sb.appendLine("    <table>")
        sb.appendLine("        <tr><th>Category</th><th>Total</th><th>Pass</th><th>Fail</th><th>Skip</th><th>Error</th></tr>")
        for ((cat, stats) in summary.byCategory.entries.sortedBy { it.key }) {
            sb.appendLine("        <tr><td>$cat</td><td>${stats.total}</td><td>${stats.passed}</td><td>${stats.failed}</td><td>${stats.skipped}</td><td>${stats.errored}</td></tr>")
        }
        sb.appendLine("    </table>")

        // Extension details
        sb.appendLine("    <h2>Extension Details</h2>")
        sb.appendLine("""    <input type="text" class="search-box" placeholder="Search extensions..." oninput="filterExtensions(this.value)">""")
        sb.appendLine("""    <div class="filters">""")
        sb.appendLine("""        <button class="filter-btn active" onclick="showAll()">All</button>""")
        sb.appendLine("""        <button class="filter-btn" onclick="showFailed()">Failed</button>""")
        sb.appendLine("""        <button class="filter-btn" onclick="showClean()">Clean</button>""")
        sb.appendLine("""    </div>""")

        for (extReport in report.extensions.sortedBy { it.moduleId }) {
            val passRate = (extReport.passRate * 100).toInt()
            sb.appendLine("""    <div class="ext-card" data-module="${extReport.moduleId}" data-failed="${extReport.failed > 0}" data-clean="${extReport.failed == 0 && extReport.errored == 0}">""")
            sb.appendLine("""        <div class="ext-header" onclick="toggleDetails(this)">""")
            sb.appendLine("""            <span class="ext-name">${extReport.moduleId}</span>""")
            sb.appendLine("""            <span class="ext-stats">${extReport.passed}/${extReport.total} ($passRate%)</span>""")
            sb.appendLine("""        </div>""")
            sb.appendLine("""        <div class="ext-details">""")
            sb.appendLine("""            <table><tr><th>Test</th><th>Status</th><th>Duration</th><th>Message</th></tr>""")
            for (result in extReport.results) {
                sb.appendLine("""                <tr><td>${result.testName}</td><td><span class="status ${result.status}">${result.status.uppercase()}</span></td><td>${result.durationMs}ms</td><td>${result.message.take(60)}</td></tr>""")
            }
            sb.appendLine("""            </table>""")
            sb.appendLine("""        </div>""")
            sb.appendLine("""    </div>""")
        }

        sb.appendLine(
            """
    <script>
        function toggleDetails(el) {
            el.nextElementSibling.classList.toggle('open');
        }
        function filterExtensions(query) {
            query = query.toLowerCase();
            document.querySelectorAll('.ext-card').forEach(card => {
                card.style.display = card.dataset.module.toLowerCase().includes(query) ? 'block' : 'none';
            });
        }
        function showAll() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            document.querySelectorAll('.ext-card').forEach(c => c.style.display = 'block');
        }
        function showFailed() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            document.querySelectorAll('.ext-card').forEach(c => c.style.display = c.dataset.failed === 'true' ? 'block' : 'none');
        }
        function showClean() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            document.querySelectorAll('.ext-card').forEach(c => c.style.display = c.dataset.clean === 'true' ? 'block' : 'none');
        }
    </script>
</div>
</body>
</html>""",
        )

        val file = File(outputDir, "report-${report.runId}.html")
        file.writeText(sb.toString())
    }
}
