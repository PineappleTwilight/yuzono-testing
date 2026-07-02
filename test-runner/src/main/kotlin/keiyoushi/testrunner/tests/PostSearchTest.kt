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
 * POST-based search tests - for themes that use POST instead of GET.
 * Mirrors Python's post_search.py.
 * Note: This is informational - we test POST search through the searchAnimeRequest method.
 */
@RegisterTest
class PostSearchTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "post_search"
    override val category = "post_search"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("post_search_load", message = "Requires API key"))
        }

        if (ext.baseUrl.isBlank()) {
            return listOf(skip("post_search_load", message = "No baseUrl defined"))
        }

        var source: AnimeHttpSource? = null
        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
        } catch (e: Exception) {
            return listOf(error("post_search_load", message = "Failed to instantiate source: ${e.message}"))
        }

        val results = mutableListOf<TestResult>()
        results.add(testPostSearchLoad(source))
        if (results.last().status == TestResult.STATUS_PASS) {
            results.add(testPostSearchHasResults(source))
        } else {
            results.add(skip("post_search_has_results", message = "POST search page did not load"))
        }
        return results
    }

    private fun testPostSearchLoad(source: AnimeHttpSource): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val request = buildSearchRequest(source, 1, "test")
            val response = source.client.newCall(request).execute()
            val duration = (System.currentTimeMillis() - start).toDouble()
            response.close()

            // Check if this looks like a POST request
            val isPost = request.method == "POST"

            if (response.isSuccessful) {
                pass("post_search_load", duration, if (isPost) "POST request succeeded" else "GET request succeeded (not POST-based)")
            } else {
                fail("post_search_load", duration, "HTTP ${response.code}")
            }
        } catch (e: Exception) {
            fail("post_search_load", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun testPostSearchHasResults(source: AnimeHttpSource): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val animesPage = searchAnime(source, 1, "naruto")
            val duration = (System.currentTimeMillis() - start).toDouble()

            if (animesPage.animes.isNotEmpty()) {
                pass("post_search_has_results", duration, "Found ${animesPage.animes.size} results")
            } else {
                fail("post_search_has_results", duration, "No results found")
            }
        } catch (e: Exception) {
            fail("post_search_has_results", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun buildSearchRequest(source: AnimeHttpSource, page: Int, query: String): Request {
        try {
            val method: Method = source.javaClass.getMethod("searchAnimeRequest", Int::class.java, String::class.java, AnimeFilterList::class.java)
            @Suppress("UNCHECKED_CAST")
            return method.invoke(source, page, query, AnimeFilterList()) as Request
        } catch (_: Exception) {
            // Fall back
        }

        val method: Method = source.javaClass.getMethod("popularAnimeRequest", Int::class.java)
        return method.invoke(source, 1) as Request
    }

    private fun searchAnime(source: AnimeHttpSource, page: Int, query: String): AnimesPage {
        try {
            val method: Method = source.javaClass.getMethod("getSearchAnime", Int::class.java, String::class.java, AnimeFilterList::class.java)
            val result = method.invoke(source, page, query, AnimeFilterList())
            if (result is AnimesPage) return result
            if (result is java.util.concurrent.Future<*>) {
                @Suppress("UNCHECKED_CAST")
                return (result as java.util.concurrent.Future<AnimesPage>).get()
            }
        } catch (_: Exception) {
            // Fall through
        }

        val request = buildSearchRequest(source, page, query)
        val response = source.client.newCall(request).execute()

        val parseMethod: Method = source.javaClass.getMethod("searchAnimeParse", okhttp3.Response::class.java)
        @Suppress("UNCHECKED_CAST")
        return parseMethod.invoke(source, response) as AnimesPage
    }
}
