package keiyoushi.testrunner.tests

import eu.kanade.tachiyomi.animesource.model.AnimesPage
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import keiyoushi.testframework.model.ExtensionMeta
import keiyoushi.testrunner.bootstrap.SourceRunner
import keiyoushi.testrunner.model.TestResult
import okhttp3.Request
import java.lang.reflect.Method

/**
 * Popular anime tests - verify popularAnime endpoint returns entries.
 * Mirrors Python's popular.py.
 */
@RegisterTest
class PopularTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "popular"
    override val category = "popular"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("popular_page_load", message = "Requires API key"))
        }

        if (ext.baseUrl.isBlank()) {
            return listOf(skip("popular_page_load", message = "No baseUrl defined"))
        }

        var source: AnimeHttpSource? = null
        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
        } catch (e: Exception) {
            return listOf(error("popular_page_load", message = "Failed to instantiate source: ${e.message}"))
        }

        val results = mutableListOf<TestResult>()
        results.add(testPopularPageLoad(source))
        if (results.last().status == TestResult.STATUS_PASS) {
            results.add(testPopularHasEntries(source))
        } else {
            results.add(skip("popular_has_entries", message = "Popular page did not load"))
        }
        return results
    }

    private fun testPopularPageLoad(source: AnimeHttpSource): TestResult {
        val start = System.currentTimeMillis()
        return try {
            // Use reflection to call popularAnimeRequest(1)
            val requestMethod: Method = source.javaClass.getMethod("popularAnimeRequest", Int::class.java)
            val request = requestMethod.invoke(source, 1) as Request

            // Execute the request
            val response = source.client.newCall(request).execute()
            val duration = (System.currentTimeMillis() - start).toDouble()
            response.close()

            if (response.isSuccessful) {
                pass("popular_page_load", duration, "HTTP ${response.code}")
            } else {
                fail("popular_page_load", duration, "HTTP ${response.code}")
            }
        } catch (e: Exception) {
            fail("popular_page_load", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun testPopularHasEntries(source: AnimeHttpSource): TestResult {
        val start = System.currentTimeMillis()
        return try {
            // Get popular anime page
            val animesPage = getPopularAnime(source, 1)
            val duration = (System.currentTimeMillis() - start).toDouble()

            if (animesPage.animes.isNotEmpty()) {
                pass("popular_has_entries", duration, "Found ${animesPage.animes.size} anime entries")
            } else {
                fail("popular_has_entries", duration, "No anime entries found")
            }
        } catch (e: Exception) {
            fail("popular_has_entries", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    /**
     * Call getPopularAnime via reflection to get the AnimesPage.
     * Tries newer suspend function first, falls back to older non-suspend version.
     */
    private fun getPopularAnime(source: AnimeHttpSource, page: Int): AnimesPage {
        // Try getPopularAnime (newer async version)
        try {
            val method: Method = source.javaClass.getMethod("getPopularAnime", Int::class.java)
            val result = method.invoke(source, page)
            if (result is AnimesPage) return result
            if (result is java.util.concurrent.Future<*>) {
                @Suppress("UNCHECKED_CAST")
                return (result as java.util.concurrent.Future<AnimesPage>).get()
            }
        } catch (_: Exception) {
            // Fall through to old method
        }

        // Fall back to popularAnimeRequest + popularAnimeParse (older synchronous version)
        val requestMethod: Method = source.javaClass.getMethod("popularAnimeRequest", Int::class.java)
        val request = requestMethod.invoke(source, 1) as Request
        val response = source.client.newCall(request).execute()

        val parseMethod: Method = source.javaClass.getMethod("popularAnimeParse", okhttp3.Response::class.java)
        @Suppress("UNCHECKED_CAST")
        return parseMethod.invoke(source, response) as AnimesPage
    }
}
