package keiyoushi.testrunner.tests

import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import keiyoushi.testframework.model.ExtensionMeta
import keiyoushi.testrunner.bootstrap.SourceRunner
import keiyoushi.testrunner.model.TestResult
import okhttp3.Request

/**
 * Connectivity tests - verify baseUrl reachability.
 * Mirrors Python's connectivity.py (5 checks).
 */
@RegisterTest
class ConnectivityTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "connectivity"
    override val category = "connectivity"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        if (ext.requiresApiKey && !config.includeApiKeyExtensions) {
            return listOf(skip("connectivity", message = "Requires API key"))
        }

        val results = mutableListOf<TestResult>()
        var source: AnimeHttpSource? = null

        try {
            source = SourceRunner.createExtension<AnimeHttpSource>(ext)
            val baseUrl = source.baseUrl

            if (baseUrl.isBlank()) {
                return listOf(skip("connectivity", message = "No baseUrl defined"))
            }

            // Test 1: base_url_reachable - can we make a request?
            results.add(testBaseUrlReachable(source, baseUrl))

            // Test 2: base_url_status_200 - does it return 2xx?
            if (results.last().status == TestResult.STATUS_PASS) {
                results.add(testBaseUrlStatus200(source, baseUrl))
            } else {
                results.add(skip("base_url_status_200", message = "Base URL not reachable"))
            }

            // Test 3: base_url_no_cloudflare - is it blocked?
            if (results.any { it.status == TestResult.STATUS_PASS && it.testName.contains("status") }) {
                results.add(testNoCloudflare(source, baseUrl))
            } else {
                results.add(skip("base_url_no_cloudflare", message = "Skipped due to connectivity issues"))
            }
        } catch (e: Exception) {
            return listOf(error("connectivity", message = "Failed to instantiate source: ${e.message}"))
        }

        return results
    }

    private fun testBaseUrlReachable(source: AnimeHttpSource, baseUrl: String): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val request = Request.Builder().url(baseUrl).build()
            val response = source.client.newCall(request).execute()
            val duration = (System.currentTimeMillis() - start).toDouble()

            if (response.isSuccessful || response.code in 300..399) {
                pass("base_url_reachable", duration, "HTTP ${response.code} from $baseUrl")
            } else {
                fail("base_url_reachable", duration, "HTTP ${response.code} from $baseUrl")
            }
        } catch (e: Exception) {
            fail("base_url_reachable", (System.currentTimeMillis() - start).toDouble(), "Connection failed: ${e.message}")
        }
    }

    private fun testBaseUrlStatus200(source: AnimeHttpSource, baseUrl: String): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val request = Request.Builder().url(baseUrl).build()
            val response = source.client.newCall(request).execute()
            val duration = (System.currentTimeMillis() - start).toDouble()
            response.close()

            if (response.isSuccessful) {
                pass("base_url_status_200", duration, "HTTP ${response.code} from $baseUrl")
            } else {
                fail("base_url_status_200", duration, "Expected 2xx, got ${response.code}")
            }
        } catch (e: Exception) {
            fail("base_url_status_200", (System.currentTimeMillis() - start).toDouble(), "Request failed: ${e.message}")
        }
    }

    private fun testNoCloudflare(source: AnimeHttpSource, baseUrl: String): TestResult {
        val start = System.currentTimeMillis()
        return try {
            val request = Request.Builder().url(baseUrl).build()
            val response = source.client.newCall(request).execute()
            val body = response.body?.string() ?: ""
            response.close()
            val duration = (System.currentTimeMillis() - start).toDouble()

            val cfMarkers = listOf(
                "cf-ray",
                "Cloudflare",
                "Checking your browser",
                "rayid=",
            )

            val hasCloudflare = cfMarkers.any { it in body } || response.header("cf-ray") != null

            if (hasCloudflare) {
                fail("base_url_no_cloudflare", duration, "Cloudflare protection detected")
            } else {
                pass("base_url_no_cloudflare", duration, "No Cloudflare detected")
            }
        } catch (e: Exception) {
            skip("base_url_no_cloudflare", (System.currentTimeMillis() - start).toDouble(), "Could not check: ${e.message}")
        }
    }
}
