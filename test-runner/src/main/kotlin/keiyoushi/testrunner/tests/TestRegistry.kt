package keiyoushi.testrunner.tests

import kotlin.reflect.KClass

/**
 * Registry for test categories using annotation-based discovery.
 */
@Target(AnnotationTarget.CLASS)
@Retention(AnnotationRetention.RUNTIME)
annotation class RegisterTest

/**
 * Registry that collects all ExtensionTest subclasses.
 * Mirrors Python's @register_test decorator and get_all_tests().
 */
object TestRegistry {
    private val registeredTests = mutableListOf<KClass<out ExtensionTest>>()

    /**
     * Register a test class.
     */
    fun register(cls: KClass<out ExtensionTest>): KClass<out ExtensionTest> {
        registeredTests.add(cls)
        return cls
    }

    /**
     * Get all registered test instances filtered by config.
     */
    fun getTests(config: TestConfig): List<ExtensionTest> {
        val categoryFilter = config.testCategories.ifEmpty { TestCategory.all() }

        return registeredTests
            .filter { cls -> cls.objectInstance != null || categoryFilter.contains(cls.simpleName?.lowercase()) }
            .mapNotNull { cls ->
                try {
                    cls.objectInstance ?: cls.java.getDeclaredConstructor(TestConfig::class.java).newInstance(config)
                } catch (e: Exception) {
                    null
                }
            }
            .filter { it.category in categoryFilter }
    }

    /**
     * Get all registered test classes.
     */
    fun getTestClasses(): List<KClass<out ExtensionTest>> = registeredTests.toList()
}

/**
 * Helper annotation to register a test class.
 */
fun registerTest(cls: KClass<out ExtensionTest>): KClass<out ExtensionTest> = TestRegistry.register(cls)
