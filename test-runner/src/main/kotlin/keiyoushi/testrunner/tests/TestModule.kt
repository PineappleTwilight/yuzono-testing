package keiyoushi.testrunner.tests

import kotlin.reflect.KClass

/**
 * Test module - registers all test categories.
 * Import this to ensure all tests are registered.
 */
object TestModule {

    private val registeredTests = listOf<KClass<out ExtensionTest>>(
        StructuralTest::class,
        ConnectivityTest::class,
        PopularTest::class,
        SearchTest::class,
        LatestTest::class,
        DetailsTest::class,
        EpisodesTest::class,
        FiltersTest::class,
        SeriesDetailsTest::class,
        EpisodeListTest::class,
        VideoStreamsTest::class,
        PaginationTest::class,
        PostSearchTest::class,
    )

    /**
     * Get all registered test classes.
     */
    fun getTestClasses(): List<KClass<out ExtensionTest>> = registeredTests

    /**
     * Get test instances filtered by config.
     */
    fun getTests(config: TestConfig): List<ExtensionTest> {
        val categoryFilter = config.testCategories.ifEmpty { TestCategory.all() }

        return registeredTests
            .filter { cls ->
                val testName = cls.simpleName?.removeSuffix("Test")?.lowercase() ?: ""
                categoryFilter.contains(testName)
            }
            .mapNotNull { cls ->
                try {
                    cls.java.getDeclaredConstructor(TestConfig::class.java).newInstance(config)
                } catch (e: Exception) {
                    null
                }
            }
            .filter { it.category in categoryFilter }
    }
}
