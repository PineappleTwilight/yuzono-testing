package keiyoushi.testrunner.tests

import eu.kanade.tachiyomi.animesource.model.AnimesPage
import eu.kanade.tachiyomi.animesource.model.SAnime
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import keiyoushi.testframework.model.ExtensionMeta
import keiyoushi.testrunner.bootstrap.SourceRunner
import keiyoushi.testrunner.model.TestResult
import okhttp3.Request
import java.lang.reflect.Method

/**
 * Details tests - verify series detail pages load with expected fields.
 * Mirrors Python's details.py.
 */
@RegisterTest
class DetailsTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "details"
    override val category = "details"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("detail_page_load", message = "Requires API key"))
        }

        if (ext.baseUrl.isBlank()) {
            return listOf(skip("detail_page_load", message = "No baseUrl defined"))
        }

        var source: AnimeHttpSource? = null
        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
        } catch (e: Exception) {
            return listOf(error("detail_page_load", message = "Failed to instantiate source: ${e.message}"))
        }

        val results = mutableListOf<TestResult>()

        // First get a sample anime from popular list
        val sampleAnime = getSampleAnime(source)
        if (sampleAnime == null) {
            return listOf(skip("detail_page_load", message = "Could not get sample anime from popular list"))
        }

        results.add(testDetailPageLoad(source, sampleAnime))
        if (results.last().status == TestResult.STATUS_PASS) {
            results.add(testDetailHasContent(source, sampleAnime))
        } else {
            results.add(skip("detail_has_content", message = "Detail page did not load"))
        }
        return results
    }

    private fun getSampleAnime(source: AnimeHttpSource): SAnime? = try {
        val animesPage = getPopularAnime(source, 1)
        animesPage.animes.firstOrNull()
    } catch (_: Exception) {
        null
    }

    private fun getPopularAnime(source: AnimeHttpSource, page: Int): AnimesPage {
        val requestMethod: Method = source.javaClass.getMethod("popularAnimeRequest", Int::class.java)
        val request = requestMethod.invoke(source, 1) as Request
        val response = source.client.newCall(request).execute()

        val parseMethod: Method = source.javaClass.getMethod("popularAnimeParse", okhttp3.Response::class.java)
        @Suppress("UNCHECKED_CAST")
        return parseMethod.invoke(source, response) as AnimesPage
    }

    private fun testDetailPageLoad(source: AnimeHttpSource, anime: SAnime): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val request = buildDetailsRequest(source, anime)
            val response = source.client.newCall(request).execute()
            val duration = (System.currentTimeMillis() - start).toDouble()
            response.close()

            if (response.isSuccessful) {
                pass("detail_page_load", duration, "HTTP ${response.code}")
            } else {
                fail("detail_page_load", duration, "HTTP ${response.code}")
            }
        } catch (e: Exception) {
            fail("detail_page_load", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun testDetailHasContent(source: AnimeHttpSource, anime: SAnime): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val detailedAnime = getAnimeDetails(source, anime)
            val duration = (System.currentTimeMillis() - start).toDouble()

            // Check for at least 2 of: title, description, thumbnail
            var contentCount = 0
            if (detailedAnime.title.isNotBlank()) contentCount++
            val desc = detailedAnime.description
            if (!desc.isNullOrBlank() && desc.length > 20) contentCount++
            val thumb = detailedAnime.thumbnail_url ?: ""
            if (thumb.isNotBlank()) contentCount++

            if (contentCount >= 2) {
                pass("detail_has_content", duration, "Found $contentCount content fields")
            } else {
                fail("detail_has_content", duration, "Only $contentCount content fields found")
            }
        } catch (e: Exception) {
            fail("detail_has_content", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun buildDetailsRequest(source: AnimeHttpSource, anime: SAnime): Request {
        val method: Method = source.javaClass.getMethod("animeDetailsRequest", SAnime::class.java)
        return method.invoke(source, anime) as Request
    }

    private fun getAnimeDetails(source: AnimeHttpSource, anime: SAnime): SAnime {
        // Try getAnimeDetails (newer async version)
        try {
            val method: Method = source.javaClass.getMethod("getAnimeDetails", SAnime::class.java)
            val result = method.invoke(source, anime)
            if (result is SAnime) return result
            if (result is java.util.concurrent.Future<*>) {
                @Suppress("UNCHECKED_CAST")
                return (result as java.util.concurrent.Future<SAnime>).get()
            }
        } catch (_: Exception) {
            // Fall through to old method
        }

        // Fall back to animeDetailsRequest + animeDetailsParse
        val requestMethod: Method = source.javaClass.getMethod("animeDetailsRequest", SAnime::class.java)
        val request = requestMethod.invoke(source, anime) as Request
        val response = source.client.newCall(request).execute()

        val parseMethod: Method = source.javaClass.getMethod("animeDetailsParse", okhttp3.Response::class.java)
        @Suppress("UNCHECKED_CAST")
        return parseMethod.invoke(source, response) as SAnime
    }
}
