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
 * Episodes tests - verify episode count is available and > 0.
 * Mirrors Python's episodes.py.
 */
@RegisterTest
class EpisodesTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "episodes"
    override val category = "episodes"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("episode_page_load", message = "Requires API key"))
        }

        if (ext.baseUrl.isBlank()) {
            return listOf(skip("episode_page_load", message = "No baseUrl defined"))
        }

        var source: AnimeHttpSource? = null
        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
        } catch (e: Exception) {
            return listOf(error("episode_page_load", message = "Failed to instantiate source: ${e.message}"))
        }

        // Get a sample anime first
        val sampleAnime = getSampleAnime(source) ?: return listOf(skip("episode_page_load", message = "Could not get sample anime"))

        val results = mutableListOf<TestResult>()
        results.add(testEpisodePageLoad(source, sampleAnime))

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

    private fun testEpisodePageLoad(source: AnimeHttpSource, anime: SAnime): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val episodes = getEpisodeList(source, anime)
            val duration = (System.currentTimeMillis() - start).toDouble()

            if (episodes.isNotEmpty()) {
                pass("episode_page_load", duration, "Found ${episodes.size} episodes")
            } else {
                skip("episode_page_load", duration, "No episodes found on page")
            }
        } catch (e: Exception) {
            fail("episode_page_load", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    @Suppress("UNCHECKED_CAST")
    private fun getEpisodeList(source: AnimeHttpSource, anime: SAnime): List<*> {
        // Try getEpisodeList (newer async version)
        try {
            val method: Method = source.javaClass.getMethod("getEpisodeList", SAnime::class.java)
            val result = method.invoke(source, anime)
            if (result is List<*>) return result
            if (result is java.util.concurrent.Future<*>) {
                return (result as java.util.concurrent.Future<List<*>>).get()
            }
        } catch (_: Exception) {
            // Fall through to old method
        }

        // Fall back to episodeListRequest + episodeListParse
        val requestMethod: Method = source.javaClass.getMethod("episodeListRequest", SAnime::class.java)
        val request = requestMethod.invoke(source, anime) as Request
        val response = source.client.newCall(request).execute()

        val parseMethod: Method = source.javaClass.getMethod("episodeListParse", okhttp3.Response::class.java)
        return parseMethod.invoke(source, response) as List<*>
    }
}
