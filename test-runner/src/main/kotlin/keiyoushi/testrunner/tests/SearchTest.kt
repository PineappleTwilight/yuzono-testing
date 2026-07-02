package keiyoushi.testrunner.tests

import eu.kanade.tachiyomi.animesource.model.AnimeFilterList
import eu.kanade.tachiyomi.animesource.model.AnimesPage
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import keiyoushi.testframework.model.ExtensionMeta
import keiyoushi.testrunner.bootstrap.SourceRunner
import keiyoushi.testrunner.model.TestResult
import okhttp3.Request
import java.lang.reflect.Method

/**
 * Search tests - verify search endpoint returns results.
 * Mirrors Python's search.py.
 */
@RegisterTest
class SearchTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "search"
    override val category = "search"

    private val testQueries = listOf("naruto", "one piece", "dragon")

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("search_page_load", message = "Requires API key"))
        }

        if (ext.baseUrl.isBlank()) {
            return listOf(skip("search_page_load", message = "No baseUrl defined"))
        }

        var source: AnimeHttpSource? = null
        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
        } catch (e: Exception) {
            return listOf(error("search_page_load", message = "Failed to instantiate source: ${e.message}"))
        }

        val results = mutableListOf<TestResult>()
        results.add(testSearchPageLoad(source))
        if (results.last().status == TestResult.STATUS_PASS) {
            results.add(testSearchHasResults(source))
        } else {
            results.add(skip("search_has_results", message = "Search page did not load"))
        }
        return results
    }

    private fun testSearchPageLoad(source: AnimeHttpSource): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val request = buildSearchRequest(source, 1, testQueries.first())
            val response = source.client.newCall(request).execute()
            val duration = (System.currentTimeMillis() - start).toDouble()
            response.close()

            if (response.isSuccessful) {
                pass("search_page_load", duration, "HTTP ${response.code}")
            } else {
                fail("search_page_load", duration, "HTTP ${response.code}")
            }
        } catch (e: Exception) {
            fail("search_page_load", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun testSearchHasResults(source: AnimeHttpSource): TestResult {
        val start = System.currentTimeMillis()
        return try {
            for (query in testQueries) {
                try {
                    val animesPage = searchAnime(source, 1, query)
                    if (animesPage.animes.isNotEmpty()) {
                        return pass("search_has_results", (System.currentTimeMillis() - start).toDouble(), "Found ${animesPage.animes.size} results for '$query'")
                    }
                } catch (_: Exception) {
                    // Try next query
                }
            }
            fail("search_has_results", (System.currentTimeMillis() - start).toDouble(), "No results for any test query")
        } catch (e: Exception) {
            fail("search_has_results", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun buildSearchRequest(source: AnimeHttpSource, page: Int, query: String): Request {
        // Try searchAnimeRequest first
        try {
            val method: Method = source.javaClass.getMethod("searchAnimeRequest", Int::class.java, String::class.java, AnimeFilterList::class.java)
            @Suppress("UNCHECKED_CAST")
            return method.invoke(source, page, query, AnimeFilterList()) as Request
        } catch (_: Exception) {
            // Fall back to popularAnimeRequest if search not available
        }

        val requestMethod: Method = source.javaClass.getMethod("popularAnimeRequest", Int::class.java)
        return requestMethod.invoke(source, 1) as Request
    }

    private fun searchAnime(source: AnimeHttpSource, page: Int, query: String): AnimesPage {
        // Try getSearchAnime (newer async version)
        try {
            val method: Method = source.javaClass.getMethod("getSearchAnime", Int::class.java, String::class.java, AnimeFilterList::class.java)
            val result = method.invoke(source, page, query, AnimeFilterList())
            if (result is AnimesPage) return result
            if (result is java.util.concurrent.Future<*>) {
                @Suppress("UNCHECKED_CAST")
                return (result as java.util.concurrent.Future<AnimesPage>).get()
            }
        } catch (_: Exception) {
            // Fall through to old method
        }

        // Fall back to searchAnimeRequest + searchAnimeParse
        val request = buildSearchRequest(source, page, query)
        val response = source.client.newCall(request).execute()

        val parseMethod: Method = source.javaClass.getMethod("searchAnimeParse", okhttp3.Response::class.java)
        @Suppress("UNCHECKED_CAST")
        return parseMethod.invoke(source, response) as AnimesPage
    }
}
