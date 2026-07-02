package keiyoushi.testrunner.tests

import eu.kanade.tachiyomi.animesource.model.AnimesPage
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import keiyoushi.testframework.model.ExtensionMeta
import keiyoushi.testrunner.bootstrap.SourceRunner
import keiyoushi.testrunner.model.TestResult
import okhttp3.Request
import java.lang.reflect.Method

/**
 * Latest updates tests - verify latestUpdates endpoint works.
 * Mirrors Python's latest.py.
 */
@RegisterTest
class LatestTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "latest"
    override val category = "latest"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("latest_page_load", message = "Requires API key"))
        }

        if (ext.baseUrl.isBlank()) {
            return listOf(skip("latest_page_load", message = "No baseUrl defined"))
        }

        var source: AnimeHttpSource? = null
        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
        } catch (e: Exception) {
            return listOf(error("latest_page_load", message = "Failed to instantiate source: ${e.message}"))
        }

        val results = mutableListOf<TestResult>()
        results.add(testLatestPageLoad(source))
        if (results.last().status == TestResult.STATUS_PASS) {
            results.add(testLatestHasEntries(source))
        } else {
            results.add(skip("latest_has_entries", message = "Latest page did not load"))
        }
        return results
    }

    private fun testLatestPageLoad(source: AnimeHttpSource): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val request = buildLatestRequest(source, 1)
            val response = source.client.newCall(request).execute()
            val duration = (System.currentTimeMillis() - start).toDouble()
            response.close()

            if (response.isSuccessful) {
                pass("latest_page_load", duration, "HTTP ${response.code}")
            } else {
                fail("latest_page_load", duration, "HTTP ${response.code}")
            }
        } catch (e: Exception) {
            fail("latest_page_load", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun testLatestHasEntries(source: AnimeHttpSource): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val animesPage = getLatestUpdates(source, 1)
            val duration = (System.currentTimeMillis() - start).toDouble()

            if (animesPage.animes.isNotEmpty()) {
                pass("latest_has_entries", duration, "Found ${animesPage.animes.size} entries")
            } else {
                fail("latest_has_entries", duration, "No entries found")
            }
        } catch (e: Exception) {
            fail("latest_has_entries", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun buildLatestRequest(source: AnimeHttpSource, page: Int): Request {
        val method: Method = source.javaClass.getMethod("latestUpdatesRequest", Int::class.java)
        return method.invoke(source, page) as Request
    }

    private fun getLatestUpdates(source: AnimeHttpSource, page: Int): AnimesPage {
        // Try getLatestUpdates (newer async version)
        try {
            val method: Method = source.javaClass.getMethod("getLatestUpdates", Int::class.java)
            val result = method.invoke(source, page)
            if (result is AnimesPage) return result
            if (result is java.util.concurrent.Future<*>) {
                @Suppress("UNCHECKED_CAST")
                return (result as java.util.concurrent.Future<AnimesPage>).get()
            }
        } catch (_: Exception) {
            // Fall through to old method
        }

        // Fall back to latestUpdatesRequest + latestUpdatesParse
        val requestMethod: Method = source.javaClass.getMethod("latestUpdatesRequest", Int::class.java)
        val request = requestMethod.invoke(source, 1) as Request
        val response = source.client.newCall(request).execute()

        val parseMethod: Method = source.javaClass.getMethod("latestUpdatesParse", okhttp3.Response::class.java)
        @Suppress("UNCHECKED_CAST")
        return parseMethod.invoke(source, response) as AnimesPage
    }
}
