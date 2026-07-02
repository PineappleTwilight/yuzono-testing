package keiyoushi.testframework.bootstrap

import android.app.Application
import eu.kanade.tachiyomi.animeextension.en.animepahe.AnimePahe
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import eu.kanade.tachiyomi.network.NetworkHelper
import kotlinx.serialization.json.Json
import okhttp3.Headers
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import uy.kohesive.injekt.Injekt
import uy.kohesive.injekt.api.get

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class TestBootstrapTest {

    @BeforeAll
    fun setUp() {
        TestBootstrap.setUp()
    }

    @Test
    fun `Injekt has Application singleton`() {
        val app = Injekt.get<Application>()
        assertNotNull(app)
        assertTrue(app is keiyoushi.testframework.stub.StubApplication)
    }

    @Test
    fun `Injekt has Json singleton`() {
        val json = Injekt.get<Json>()
        assertNotNull(json)
        assertTrue(json.configuration.ignoreUnknownKeys)
    }

    @Test
    fun `setUp is idempotent - second call is no-op`() {
        TestBootstrap.setUp()
        TestBootstrap.setUp()
        val app = Injekt.get<Application>()
        assertNotNull(app)
    }

    @Test
    fun `isInitialized is true after setUp`() {
        assertTrue(TestBootstrap.isInitialized)
    }

    @Test
    fun `application property returns StubApplication`() {
        val app = TestBootstrap.application
        assertNotNull(app)
        assertTrue(app is keiyoushi.testframework.stub.StubApplication)
    }

    @Test
    fun `debug trace SourceInstantiator create step by step`() {
        val clazz = AnimePahe::class.java
        println("Step 1: allocateInstance")
        val instance = SourceInstantiator.allocateInstance(clazz)
        println("  instance class = ${instance.javaClass.name}")

        println("Step 2: injectBaseFields - createNetworkHelper")
        val nh = SourceInstantiator.allocateInstance(NetworkHelper::class.java)
        println("  NetworkHelper allocated: class = ${nh.javaClass.name}")

        val baseClient = okhttp3.OkHttpClient.Builder().build()
        println("  baseClient = $baseClient")

        SourceInstantiator.setField(nh, "client", baseClient)
        println("  set client on NetworkHelper")
        try {
            SourceInstantiator.setField(nh, "cloudflareClient", baseClient)
            println("  set cloudflareClient on NetworkHelper")
        } catch (e: NoSuchFieldException) {
            println("  cloudflareClient not found (expected): ${e.message}")
        }

        println("Step 3: set fields on source")
        SourceInstantiator.setField(instance, "network", nh)
        println("  set network")
        SourceInstantiator.setField(instance, "client", baseClient)
        println("  set client")
        SourceInstantiator.setField(instance, "headers", Headers.Builder().build())
        println("  set headers")
        SourceInstantiator.setField(instance, "versionId", 1)
        println("  set versionId")
        val id = computeId(instance as AnimeHttpSource, 1)
        SourceInstantiator.setField(instance, "id", id)
        println("  set id = $id")

        println("Step 4: verify fields are accessible via reflection")
        val clientField = instance.javaClass.superclass!!.getDeclaredField("client")
        clientField.isAccessible = true
        val clientValue = clientField.get(instance)
        println("  reflected client = $clientValue")

        val networkField = instance.javaClass.superclass!!.getDeclaredField("network")
        networkField.isAccessible = true
        val networkValue = networkField.get(instance)
        println("  reflected network = $networkValue")

        println("Step 5: verify public getters")
        val source = instance as AnimeHttpSource
        println("  source.client = ${source.client}")
        println("  source.name = ${source.name}")
        println("  source.lang = ${source.lang}")
        println("  source.id = ${source.id}")
        println("  source.headers = ${source.headers}")
        println("  source.baseUrl = ${source.baseUrl}")
    }

    private fun computeId(source: AnimeHttpSource, versionId: Int): Long {
        val name = source.name
        val lang = source.lang
        val prime = 31L
        var hash = 0L
        hash = hash * prime + name.hashCode()
        hash = hash * prime + lang.hashCode()
        hash = hash * prime + versionId
        return hash
    }

    @Test
    fun `AnimePahe can be instantiated via SourceInstantiator`() {
        val source = SourceInstantiator.create(AnimePahe::class.java)
        assertNotNull(source)
        assertEquals("AnimePahe", source.name)
        assertEquals("en", source.lang)
    }

    @Test
    fun `AnimePahe has a valid OkHttpClient`() {
        val source = SourceInstantiator.create(AnimePahe::class.java)
        val client = source.client
        assertNotNull(client)
    }

    @Test
    fun `AnimePahe has valid headers`() {
        val source = SourceInstantiator.create(AnimePahe::class.java)
        val headers = source.headers
        assertNotNull(headers)
    }

    @Test
    fun `AnimePahe has a positive id`() {
        val source = SourceInstantiator.create(AnimePahe::class.java)
        assertTrue(source.id > 0L)
    }

    @Test
    fun `AnimePahe preferences are accessible via getPreferences`() {
        val source = SourceInstantiator.create(AnimePahe::class.java)
        val prefs = keiyoushi.utils.getPreferences(source.id)
        assertNotNull(prefs)
        prefs.edit().putString("test_key", "test_value").apply()
        assertEquals("test_value", prefs.getString("test_key", null))
    }

    @Test
    fun `AnimePahe baseUrl is accessible`() {
        val source = SourceInstantiator.create(AnimePahe::class.java)
        val baseUrl = source.baseUrl
        assertNotNull(baseUrl)
        assertTrue(baseUrl.startsWith("https://"))
    }

    @Test
    fun `debug print id value`() {
        val source = SourceInstantiator.create(AnimePahe::class.java)
        println("source.id = ${source.id}")
        println("source.name = ${source.name}")
        println("source.lang = ${source.lang}")
        println("source.versionId = ${source.versionId}")
    }

    @Test
    fun `StubSharedPreferences supports all primitive types`() {
        val app = TestBootstrap.application
        val prefs = app.getSharedPreferences("test_prefs", 0)

        prefs.edit()
            .putString("str", "hello")
            .putInt("int", 42)
            .putLong("long", 999L)
            .putFloat("float", 3.14f)
            .putBoolean("bool", true)
            .putStringSet("set", setOf("a", "b"))
            .apply()

        assertEquals("hello", prefs.getString("str", null))
        assertEquals(42, prefs.getInt("int", 0))
        assertEquals(999L, prefs.getLong("long", 0L))
        assertEquals(3.14f, prefs.getFloat("float", 0f))
        assertEquals(true, prefs.getBoolean("bool", false))
        assertEquals(setOf("a", "b"), prefs.getStringSet("set", null))
    }
}
