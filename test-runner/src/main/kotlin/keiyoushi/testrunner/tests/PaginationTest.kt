package keiyoushi.testrunner.tests

import eu.kanade.tachiyomi.animesource.model.AnimesPage
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import keiyoushi.testframework.model.ExtensionMeta
import keiyoushi.testrunner.bootstrap.SourceRunner
import keiyoushi.testrunner.model.TestResult
import okhttp3.Request
import java.lang.reflect.Method

/**
 * Pagination tests - paginated endpoints return next-page data.
 * Mirrors Python's pagination.py.
 */
@RegisterTest
class PaginationTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "pagination"
    override val category = "pagination"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("pagination_page2", message = "Requires API key"))
        }

        if (ext.baseUrl.isBlank()) {
            return listOf(skip("pagination_page2", message = "No baseUrl defined"))
        }

        var source: AnimeHttpSource? = null
        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
        } catch (e: Exception) {
            return listOf(error("pagination_page2", message = "Failed to instantiate source: ${e.message}"))
        }

        return listOf(testPaginationPage2(source))
    }

    private fun testPaginationPage2(source: AnimeHttpSource): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val page1Anime = getPopularAnime(source, 1)
            val page2Anime = getPopularAnime(source, 2)
            val duration = (System.currentTimeMillis() - start).toDouble()

            // Check that pages are different (not 100% overlap)
            val page1Urls = page1Anime.animes.map { it.url }.toSet()
            val page2Urls = page2Anime.animes.map { it.url }.toSet()

            val overlap = page1Urls.intersect(page2Urls).size
            val totalPage2 = page2Urls.size
            val overlapPercent = if (totalPage2 > 0) overlap.toDouble() / totalPage2 else 1.0

            if (overlapPercent < 1.0) {
                pass("pagination_page2", duration, "Page 2 is different (${(overlapPercent * 100).toInt()}% overlap)")
            } else if (page2Anime.animes.isEmpty()) {
                skip("pagination_page2", duration, "Page 2 is empty (pagination may not be supported)")
            } else {
                fail("pagination_page2", duration, "Page 1 and Page 2 have ${(overlapPercent * 100).toInt()}% overlap")
            }
        } catch (e: Exception) {
            fail("pagination_page2", (System.currentTimeMillis() - start).toDouble(), "Error: ${e.message}")
        }
    }

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
            // Fall through
        }

        // Fall back to popularAnimeRequest + popularAnimeParse
        val requestMethod: Method = source.javaClass.getMethod("popularAnimeRequest", Int::class.java)
        val request = requestMethod.invoke(source, page) as Request
        val response = source.client.newCall(request).execute()

        val parseMethod: Method = source.javaClass.getMethod("popularAnimeParse", okhttp3.Response::class.java)
        @Suppress("UNCHECKED_CAST")
        return parseMethod.invoke(source, response) as AnimesPage
    }
}
