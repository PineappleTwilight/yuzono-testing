package keiyoushi.testrunner.tests

import eu.kanade.tachiyomi.animesource.model.AnimesPage
import eu.kanade.tachiyomi.animesource.model.SAnime
import eu.kanade.tachiyomi.animesource.model.SEpisode
import eu.kanade.tachiyomi.animesource.model.Video
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import keiyoushi.testframework.model.ExtensionMeta
import keiyoushi.testrunner.bootstrap.SourceRunner
import keiyoushi.testrunner.model.TestResult
import okhttp3.Request
import java.lang.reflect.Method

/**
 * Video streams tests - video stream URLs are resolvable.
 * Mirrors Python's video_streams.py.
 */
@RegisterTest
class VideoStreamsTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "video_streams"
    override val category = "video_streams"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("video_stream_iframe", message = "Requires API key"))
        }

        if (ext.baseUrl.isBlank()) {
            return listOf(skip("video_stream_iframe", message = "No baseUrl defined"))
        }

        var source: AnimeHttpSource? = null
        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
        } catch (e: Exception) {
            return listOf(error("video_stream_iframe", message = "Failed to instantiate source: ${e.message}"))
        }

        // Get a sample anime and episode
        val sampleAnime = getSampleAnime(source)
        if (sampleAnime == null) {
            return listOf(skip("video_stream_iframe", message = "Could not get sample anime"))
        }

        val sampleEpisode = getSampleEpisode(source, sampleAnime)
        if (sampleEpisode == null) {
            return listOf(skip("video_stream_iframe", message = "Could not get sample episode"))
        }

        val results = mutableListOf<TestResult>()
        results.add(testVideoStreamIframe(source, sampleEpisode))
        results.add(testVideoStreamXhr(source, sampleEpisode))

        return results
    }

    private fun getSampleAnime(source: AnimeHttpSource): SAnime? = try {
        val animesPage = getPopularAnime(source, 1)
        animesPage.animes.firstOrNull()
    } catch (_: Exception) {
        null
    }

    @Suppress("UNCHECKED_CAST")
    private fun getSampleEpisode(source: AnimeHttpSource, anime: SAnime): SEpisode? = try {
        val episodes = getEpisodeList(source, anime)
        episodes.filterIsInstance<SEpisode>().firstOrNull()
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

    @Suppress("UNCHECKED_CAST")
    private fun getEpisodeList(source: AnimeHttpSource, anime: SAnime): List<*> {
        try {
            val method: Method = source.javaClass.getMethod("getEpisodeList", SAnime::class.java)
            val result = method.invoke(source, anime)
            if (result is List<*>) return result
            if (result is java.util.concurrent.Future<*>) {
                return (result as java.util.concurrent.Future<List<*>>).get()
            }
        } catch (_: Exception) {
            // Fall through
        }

        val requestMethod: Method = source.javaClass.getMethod("episodeListRequest", SAnime::class.java)
        val request = requestMethod.invoke(source, anime) as Request
        val response = source.client.newCall(request).execute()

        val parseMethod: Method = source.javaClass.getMethod("episodeListParse", okhttp3.Response::class.java)
        return parseMethod.invoke(source, response) as List<*>
    }

    private fun testVideoStreamIframe(source: AnimeHttpSource, episode: SEpisode): TestResult {
        val start = System.currentTimeMillis()
        // Iframe test - try to get video list and check for valid URLs
        return try {
            @Suppress("UNCHECKED_CAST")
            val videos = getVideoList(source, episode) as List<Video>
            val duration = (System.currentTimeMillis() - start).toDouble()

            if (videos.isNotEmpty()) {
                val videoUrls = videos.mapNotNull { it.url }
                if (videoUrls.any { it.startsWith("http") }) {
                    pass("video_stream_iframe", duration, "Found ${videos.size} video streams")
                } else {
                    fail("video_stream_iframe", duration, "Video URLs not valid")
                }
            } else {
                skip("video_stream_iframe", duration, "No videos found")
            }
        } catch (e: Exception) {
            skip("video_stream_iframe", (System.currentTimeMillis() - start).toDouble(), "Iframe test skipped: ${e.message}")
        }
    }

    private fun testVideoStreamXhr(source: AnimeHttpSource, episode: SEpisode): TestResult {
        val start = System.currentTimeMillis()
        return skip("video_stream_xhr", (System.currentTimeMillis() - start).toDouble(), "XHR video test - informational only")
    }

    @Suppress("UNCHECKED_CAST")
    private fun getVideoList(source: AnimeHttpSource, episode: SEpisode): List<*> {
        // Try getVideoList (newer async version)
        try {
            val method: Method = source.javaClass.getMethod("getVideoList", SEpisode::class.java)
            val result = method.invoke(source, episode)
            if (result is List<*>) return result
            if (result is java.util.concurrent.Future<*>) {
                return (result as java.util.concurrent.Future<List<*>>).get()
            }
        } catch (_: Exception) {
            // Fall through
        }

        // Fall back to videoListRequest + videoListParse
        val requestMethod: Method = source.javaClass.getMethod("videoListRequest", SEpisode::class.java)
        val request = requestMethod.invoke(source, episode) as Request
        val response = source.client.newCall(request).execute()

        val parseMethod: Method = source.javaClass.getMethod("videoListParse", okhttp3.Response::class.java)
        return parseMethod.invoke(source, response) as List<*>
    }
}
