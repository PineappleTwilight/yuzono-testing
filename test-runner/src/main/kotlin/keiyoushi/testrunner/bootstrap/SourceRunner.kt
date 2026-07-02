package keiyoushi.testrunner.bootstrap

import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import keiyoushi.testframework.bootstrap.SourceInstantiator
import keiyoushi.testframework.bootstrap.TestBootstrap
import keiyoushi.testframework.model.ExtensionMeta

/**
 * Wrapper around test-framework's SourceInstantiator for use in test-runner.
 * Provides extension instantiation for reflection-based testing.
 */
object SourceRunner {

    /**
     * Initialize the test bootstrap (must be called before creating sources).
     */
    fun setUp() {
        TestBootstrap.setUp()
    }

    /**
     * Check if bootstrap has been initialized.
     */
    fun isInitialized(): Boolean = TestBootstrap.isInitialized

    /**
     * Get the Application instance.
     */
    fun getApplication() = TestBootstrap.application

    /**
     * Create an instance of an extension from its ExtensionMeta.
     */
    fun <T : AnimeHttpSource> createExtension(ext: ExtensionMeta): T {
        val className = "eu.kanade.tachiyomi.animeextension.${ext.lang}.${ext.name}.${ext.classSimpleName}"
        val clazz = Class.forName(className).asSubclass(AnimeHttpSource::class.java)
        @Suppress("UNCHECKED_CAST")
        return SourceInstantiator.create(clazz, ext.extName, ext.lang) as T
    }

    /**
     * Create an extension by class reference (for testing with known classes).
     */
    fun <T : AnimeHttpSource> createExtension(clazz: Class<T>, name: String? = null, lang: String? = null): T = SourceInstantiator.create(clazz, name, lang)
}
