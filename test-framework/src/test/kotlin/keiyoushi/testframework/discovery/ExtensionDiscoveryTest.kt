package keiyoushi.testframework.discovery

import keiyoushi.testframework.model.ExtensionMeta
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import java.io.File

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class ExtensionDiscoveryTest {

    /** Points at the cloned anime-extensions repo root. */
    private val repoDir = File(System.getProperty("user.dir")).resolveSibling(".")

    /** Navigate up to find the repo root (test-framework is inside the repo). */
    private val actualRepoDir: File by lazy {
        // When running from test-framework module, user.dir is the repo root
        var dir = repoDir
        while (dir.parentFile != null && !File(dir, "settings.gradle.kts").isFile) {
            dir = dir.parentFile
        }
        dir
    }

    @Test
    fun `discovers extensions from repo src directory`() {
        val extensions = ExtensionDiscovery.discover(actualRepoDir)
        assertTrue(extensions.isNotEmpty(), "Should discover at least one extension")
    }

    @Test
    fun `discovers AnimePahe extension`() {
        val extensions = ExtensionDiscovery.discover(actualRepoDir)
        val animePahe = extensions.find { it.name == "animepahe" && it.lang == "en" }
        assertNotNull(animePahe, "Should discover AnimePahe extension")
        assertEquals("AnimePahe", animePahe!!.extName)
        assertEquals(".AnimePahe", animePahe.extClass)
        assertEquals("en", animePahe.lang)
        assertEquals("en.animepahe", animePahe.moduleId)
    }

    @Test
    fun `AnimePahe has correct metadata fields`() {
        val extensions = ExtensionDiscovery.discover(actualRepoDir)
        val animePahe = extensions.find { it.name == "animepahe" && it.lang == "en" }
        assertNotNull(animePahe, "Should discover AnimePahe extension")
        assertTrue(animePahe!!.extVersionCode > 0, "extVersionCode should be positive")
        assertEquals("AnimePahe", animePahe.classSimpleName)
        assertEquals(false, animePahe.isNsfw)
        assertEquals(false, animePahe.isMultisrc, "AnimePahe is not a multisrc extension")
    }

    @Test
    fun `discoverLanguages returns non-empty list`() {
        val languages = ExtensionDiscovery.discoverLanguages(actualRepoDir)
        assertTrue(languages.isNotEmpty(), "Should discover at least one language")
        assertTrue("en" in languages, "English should be among discovered languages")
    }

    @Test
    fun `filter by language works`() {
        val allExtensions = ExtensionDiscovery.discover(actualRepoDir)
        val filtered = ExtensionDiscovery.filter(allExtensions, languages = setOf("en"))
        assertTrue(filtered.isNotEmpty())
        assertTrue(filtered.all { it.lang == "en" })
    }

    @Test
    fun `filter by extension name works`() {
        val allExtensions = ExtensionDiscovery.discover(actualRepoDir)
        val filtered = ExtensionDiscovery.filter(
            allExtensions,
            extensionNames = setOf("animepahe"),
            skipApiKeyExtensions = false,
        )
        assertTrue(filtered.isNotEmpty())
        assertTrue(filtered.any { it.name == "animepahe" })
    }

    @Test
    fun `classSimpleName strips leading dot`() {
        val meta = ExtensionMeta(
            lang = "en",
            name = "test",
            extName = "Test",
            extClass = ".TestClass",
        )
        assertEquals("TestClass", meta.classSimpleName)
    }

    @Test
    fun `isMultisrc returns true when themePkg is set`() {
        val multisrc = ExtensionMeta(
            lang = "en",
            name = "test",
            extName = "Test",
            extClass = ".TestClass",
            themePkg = "dopeflix",
        )
        val legacy = ExtensionMeta(
            lang = "en",
            name = "test2",
            extName = "Test2",
            extClass = ".TestClass2",
        )
        assertTrue(multisrc.isMultisrc)
        assertEquals(false, legacy.isMultisrc)
    }
}
