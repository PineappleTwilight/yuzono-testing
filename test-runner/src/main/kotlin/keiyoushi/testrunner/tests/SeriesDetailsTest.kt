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
 * Series details tests - deep series metadata validation.
 * Mirrors Python's series_details.py.
 */
@RegisterTest
class SeriesDetailsTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "series_details"
    override val category = "series_details"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("detail_title", message = "Requires API key"))
        }

        if (ext.baseUrl.isBlank()) {
            return listOf(skip("detail_title", message = "No baseUrl defined"))
        }

        var source: AnimeHttpSource? = null
        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
        } catch (e: Exception) {
            return listOf(error("detail_title", message = "Failed to instantiate source: ${e.message}"))
        }

        // Get a sample anime first
        val sampleAnime = getSampleAnime(source)
        if (sampleAnime == null) {
            return listOf(skip("detail_title", message = "Could not get sample anime"))
        }

        // Get detailed anime
        val detailedAnime = try {
            getAnimeDetails(source, sampleAnime)
        } catch (e: Exception) {
            return listOf(error("detail_title", message = "Failed to get anime details: ${e.message}"))
        }

        val results = mutableListOf<TestResult>()
        results.add(testDetailTitle(detailedAnime))
        results.add(testDetailDescription(detailedAnime))
        results.add(testDetailThumbnail(detailedAnime))
        results.add(testDetailGenres(detailedAnime))

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

    private fun testDetailTitle(anime: SAnime): TestResult {
        val start = System.currentTimeMillis()
        return if (anime.title.isNotBlank()) {
            pass("detail_title", (System.currentTimeMillis() - start).toDouble(), "Title: ${anime.title.take(50)}")
        } else {
            fail("detail_title", (System.currentTimeMillis() - start).toDouble(), "Title is empty")
        }
    }

    private fun testDetailDescription(anime: SAnime): TestResult {
        val start = System.currentTimeMillis()
        val desc = anime.description ?: ""
        return if (desc.length >= 20) {
            pass("detail_description", (System.currentTimeMillis() - start).toDouble(), "Description length: ${desc.length}")
        } else if (desc.isNotBlank()) {
            skip("detail_description", (System.currentTimeMillis() - start).toDouble(), "Description too short: ${desc.length} chars")
        } else {
            fail("detail_description", (System.currentTimeMillis() - start).toDouble(), "Description is empty")
        }
    }

    private fun testDetailThumbnail(anime: SAnime): TestResult {
        val start = System.currentTimeMillis()
        val thumb = anime.thumbnail_url ?: ""
        return if (thumb.isNotBlank() && (thumb.startsWith("http://") || thumb.startsWith("https://"))) {
            pass("detail_thumbnail", (System.currentTimeMillis() - start).toDouble(), "Thumbnail URL present")
        } else {
            skip("detail_thumbnail", (System.currentTimeMillis() - start).toDouble(), "Thumbnail URL missing or invalid")
        }
    }

    private fun testDetailGenres(anime: SAnime): TestResult {
        val start = System.currentTimeMillis()

        @Suppress("UNCHECKED_CAST")
        val genres = anime.genre?.let { g ->
            when (g) {
                is List<*> -> g as? List<String> ?: emptyList()
                is String -> if (g.isNotEmpty()) listOf(g) else emptyList()
                else -> emptyList()
            }
        } ?: emptyList()
        val genreCount = genres.size
        return if (genreCount > 0) {
            pass("detail_genres", (System.currentTimeMillis() - start).toDouble(), "Found $genreCount genres")
        } else {
            skip("detail_genres", (System.currentTimeMillis() - start).toDouble(), "No genres defined")
        }
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
