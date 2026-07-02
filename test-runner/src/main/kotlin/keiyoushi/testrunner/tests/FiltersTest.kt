package keiyoushi.testrunner.tests

import eu.kanade.tachiyomi.animesource.model.AnimeFilterList
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import keiyoushi.testframework.model.ExtensionMeta
import keiyoushi.testrunner.bootstrap.SourceRunner
import keiyoushi.testrunner.model.TestResult
import java.lang.reflect.Method

/**
 * Filters tests - verify filter/category system is accessible.
 * Mirrors Python's filters.py.
 */
@RegisterTest
class FiltersTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "filters"
    override val category = "filters"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("filter_page_load", message = "Requires API key"))
        }

        if (ext.baseUrl.isBlank()) {
            return listOf(skip("filter_page_load", message = "No baseUrl defined"))
        }

        var source: AnimeHttpSource? = null
        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
        } catch (e: Exception) {
            return listOf(error("filter_page_load", message = "Failed to instantiate source: ${e.message}"))
        }

        val results = mutableListOf<TestResult>()
        results.add(testFilterPageLoad(source))
        if (results.last().status == TestResult.STATUS_PASS) {
            results.add(testFilterParamsWork(source))
        } else {
            results.add(skip("filter_params_work", message = "Filter page did not load"))
        }
        return results
    }

    private fun testFilterPageLoad(source: AnimeHttpSource): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val filterList = getFilterList(source)
            val duration = (System.currentTimeMillis() - start).toDouble()

            if (filterList.isNotEmpty()) {
                pass("filter_page_load", duration, "Filter list returned ${filterList.size} filters")
            } else {
                skip("filter_page_load", duration, "No filters defined for this source")
            }
        } catch (e: Exception) {
            fail("filter_page_load", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun testFilterParamsWork(source: AnimeHttpSource): TestResult {
        val start = System.currentTimeMillis()
        return try {
            // Just verify we can create a filter list and it has expected structure
            val filterList = getFilterList(source)
            val duration = (System.currentTimeMillis() - start).toDouble()

            // Check that filters have some content (not all empty)
            val hasFilters = filterList.isNotEmpty()

            if (hasFilters) {
                pass("filter_params_work", duration, "Filters are accessible")
            } else {
                skip("filter_params_work", duration, "Filter structure present but empty")
            }
        } catch (e: Exception) {
            fail("filter_params_work", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun getFilterList(source: AnimeHttpSource): AnimeFilterList {
        val method: Method = source.javaClass.getMethod("getFilterList")
        return method.invoke(source) as AnimeFilterList
    }
}
