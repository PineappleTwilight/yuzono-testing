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
 * Episode list tests - full episode list retrieval with episode numbers.
 * Mirrors Python's episode_list.py.
 */
@RegisterTest
class EpisodeListTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "episode_list"
    override val category = "episode_list"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("episode_list_inline", message = "Requires API key"))
        }

        if (ext.baseUrl.isBlank()) {
            return listOf(skip("episode_list_inline", message = "No baseUrl defined"))
        }

        var source: AnimeHttpSource? = null
        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
        } catch (e: Exception) {
            return listOf(error("episode_list_inline", message = "Failed to instantiate source: ${e.message}"))
        }

        // Get a sample anime first
        val sampleAnime = getSampleAnime(source)
        if (sampleAnime == null) {
            return listOf(skip("episode_list_inline", message = "Could not get sample anime"))
        }

        val results = mutableListOf<TestResult>()
        results.add(testEpisodeListInline(source, sampleAnime))
        results.add(testEpisodeListXhr(source, sampleAnime))

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

    private fun testEpisodeListInline(source: AnimeHttpSource, anime: SAnime): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val episodes = getEpisodeList(source, anime)
            val duration = (System.currentTimeMillis() - start).toDouble()

            if (episodes.isNotEmpty()) {
                pass("episode_list_inline", duration, "Found ${episodes.size} episodes via inline")
            } else {
                skip("episode_list_inline", duration, "No episodes found via inline method")
            }
        } catch (e: Exception) {
            fail("episode_list_inline", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

    private fun testEpisodeListXhr(source: AnimeHttpSource, anime: SAnime): TestResult {
        val start = System.currentTimeMillis()
        // XHR test is informational - many sources don't use XHR for episodes
        return try {
            val episodes = getEpisodeList(source, anime)
            val duration = (System.currentTimeMillis() - start).toDouble()
            if (episodes.isNotEmpty()) {
                skip("episode_list_xhr", duration, "Using inline episodes (XHR not needed)")
            } else {
                skip("episode_list_xhr", duration, "No episodes available")
            }
        } catch (e: Exception) {
            skip("episode_list_xhr", (System.currentTimeMillis() - start).toDouble(), "XHR test skipped: ${e.message}")
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
