package keiyoushi.testframework.bootstrap

import android.app.Application
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import eu.kanade.tachiyomi.network.NetworkHelper
import okhttp3.Headers
import okhttp3.OkHttpClient
import java.lang.invoke.MethodHandles
import java.lang.reflect.Field
import java.lang.reflect.Modifier

/**
 * Instantiates [AnimeHttpSource] subclasses in JVM unit tests where the
 * aniyomi-lib JAR only contains API stubs.
 *
 * The aniyomi-extensions-lib ships as a stub JAR — every constructor throws
 * `Exception("Stub!")`. Normal `newInstance()` calls always fail.
 * This class uses [sun.misc.Unsafe] to allocate the object **without** calling
 * any constructor, then sets the private fields that [AnimeHttpSource] would
 * normally initialise:
 *
 * | Field       | Type            | Value                                          |
 * |-------------|-----------------|------------------------------------------------|
 * | `network`   | [NetworkHelper] | Unsafe-allocated with OkHttpClient fields set   |
 * | `client`    | [OkHttpClient]  | `network.client`                               |
 * | `headers`   | [Headers]       | empty headers (safe fallback)                  |
 * | `versionId` | `Int`           | `1`                                            |
 * | `id`        | `Long`          | generated from `name`, `lang`, `versionId`     |
 *
 * Usage:
 * ```kotlin
 * TestBootstrap.setUp()
 * val source = SourceInstantiator.create(AnimePahe::class.java)
 * ```
 */
object SourceInstantiator {

    private val unsafe: sun.misc.Unsafe by lazy {
        val field = sun.misc.Unsafe::class.java.getDeclaredField("theUnsafe")
        field.isAccessible = true
        @Suppress("UNCHECKED_CAST")
        field.get(null) as sun.misc.Unsafe
    }

    /**
     * Create an instance of [T] without calling any constructor.
     *
     * @param clazz the concrete subclass of [AnimeHttpSource]
     * @param name the source name (e.g. "AnimePahe"). If null, attempts to read
     *   from the class's `name` property getter (may return null if uninitialized).
     * @param lang the source language code (e.g. "en"). If null, attempts to read
     *   from the class's `lang` property getter (may return null if uninitialized).
     * @param configurePreferences optional lambda to pre-populate the source's
     *   SharedPreferences (e.g. set API keys, domain preferences). The lambda
     *   receives the [Application] so it can call
     *   `app.getSharedPreferences("source_$sourceId", 0)` after [id] is known.
     * @return a fully-initialised instance of [T]
     */
    @Suppress("UNCHECKED_CAST")
    fun <T : AnimeHttpSource> create(
        clazz: Class<T>,
        name: String? = null,
        lang: String? = null,
        configurePreferences: ((Application) -> Unit)? = null,
    ): T {
        val instance = allocateInstance(clazz)
        injectBaseFields(instance, name, lang)
        configurePreferences?.invoke(TestBootstrap.application)
        return instance
    }

    /**
     * Allocate an instance of [clazz] using [sun.misc.Unsafe] — skips **all**
     * constructors (including the stub constructor of [AnimeHttpSource]).
     */
    fun <T> allocateInstance(clazz: Class<T>): T {
        @Suppress("UNCHECKED_CAST")
        return unsafe.allocateInstance(clazz) as T
    }

    /**
     * Set the private fields of [AnimeHttpSource] that the stub constructor
     * would normally initialise.
     *
     * Field layout (from javap on the stub JAR):
     * ```
     * private final NetworkHelper network;
     * private final int versionId;
     * private final long id;
     * private final Headers headers;
     * private final OkHttpClient client;
     * ```
     */
    fun injectBaseFields(source: AnimeHttpSource, name: String?, lang: String?) {
        val networkHelper = createNetworkHelper()
        val client = networkHelper.client
        val headers = Headers.Builder().build()
        val versionId = 1

        // Use provided name/lang, or fall back to reading from property getters
        // (which may return null if fields aren't initialised yet)
        val resolvedName = name ?: readStringPropertySafe(source, "name") ?: source.javaClass.simpleName
        val resolvedLang = lang ?: readStringPropertySafe(source, "lang") ?: "en"

        // Set AnimeHttpSource fields
        setField(source, "network", networkHelper)
        setField(source, "client", client)
        setField(source, "headers", headers)
        setField(source, "versionId", versionId)

        // Set concrete class fields (name, lang) that the stub constructor would initialise
        setField(source, "name", resolvedName)
        setField(source, "lang", resolvedLang)

        // Generate and set id using the actual name/lang values
        val id = generateId(resolvedName, resolvedLang, versionId)
        setField(source, "id", id)

        // Initialize lazy delegates for properties like baseUrl, preferences
        initializeLazyDelegates(source)
    }

/**
     * Initialize Kotlin lazy delegates for properties that use `by lazy { ... }`.
     * The stub constructor would normally set these, but we skip it.
     */
    private fun initializeLazyDelegates(source: Any) {
        val clazz = source.javaClass
        val lazyType = kotlin.Lazy::class.java
        val delegateSuffix = "\$delegate"
        for (field in clazz.declaredFields) {
            // Skip static fields - they belong to the class, not the instance
            if (Modifier.isStatic(field.modifiers)) continue
            val fieldName = field.name
            if (fieldName.endsWith(delegateSuffix) && lazyType.isAssignableFrom(field.type)) {
                val propertyName = fieldName.substring(0, fieldName.lastIndexOf(delegateSuffix))
                val lazyInstance = createLazyDelegate(source, propertyName)
                field.isAccessible = true
                field.set(source, lazyInstance)
            }
        }
    }

    /**
     * Create a Lazy delegate for the given property.
     * For known properties like baseUrl, we compute the actual value.
     * For others, we create a Lazy that returns null (will trigger NPE if accessed).
     */
    private fun createLazyDelegate(source: Any, propertyName: String): kotlin.Lazy<*> {
        return object : kotlin.Lazy<Any?> {
            private var lazyValue: Any? = null
            private var lazyInitialized = false

            override val value: Any?
                get() {
                    if (!lazyInitialized) {
                        synchronized(this) {
                            if (!lazyInitialized) {
                                lazyValue = when (propertyName) {
                                    "baseUrl" -> computeBaseUrl(source)
                                    "preferences" -> getStubPreferences()
                                    else -> null
                                }
                                lazyInitialized = true
                            }
                        }
                    }
                    return lazyValue
                }

            override fun isInitialized(): Boolean = lazyInitialized
        }
    }

    /**
     * Create stub preferences for testing.
     * In real usage, preferences would be populated from source configuration.
     */
    private fun getStubPreferences(): Any {
        return object {
            fun getString(key: String, default: String?): String? = default
            fun getInt(key: String, default: Int): Int = default
            fun getBoolean(key: String, default: Boolean): Boolean = default
            fun edit(): Any = this
            fun putString(key: String, value: String?) {}
            fun putInt(key: String, value: Int) {}
            fun putBoolean(key: String, value: Boolean) {}
            fun apply() {}
            fun commit(): Boolean = true
        }
    }

    private fun computeBaseUrl(source: Any): String {
        val validDomains = listOf("https://animepahe.pw", "https://animepahe.com", "https://animepahe.org")
        // Return a sensible default - real baseUrl would come from source configuration
        return validDomains.first()
    }

    /**
     * Read a String property value safely - returns null if getter returns null.
     */
    private fun readStringPropertySafe(source: Any, propertyName: String): String? {
        val getterName = "get" + propertyName.replaceFirstChar { it.uppercase() }
        try {
            val getter = source.javaClass.getMethod(getterName)
            @Suppress("UNCHECKED_CAST")
            return getter.invoke(source) as String?
        } catch (_: Exception) {
            return null
        }
    }

    /**
     * Build a [NetworkHelper]. Its constructor is a stub, so we also use
     * Unsafe allocation and set the two OkHttpClient fields directly.
     */
    private fun createNetworkHelper(): NetworkHelper {
        val nh = allocateInstance(NetworkHelper::class.java)
        val baseClient = OkHttpClient.Builder().build()
        // Runtime NetworkHelper has only 'client' field; cloudflareClient is either a getter
        // or was removed. We set both if present.
        setField(nh, "client", baseClient)
        try {
            setField(nh, "cloudflareClient", baseClient)
        } catch (_: NoSuchFieldException) {
            // Ignore - not present in runtime class
        }
        return nh
    }

    /**
     * Mirror the id generation from AnimeHttpSource:
     * `generateId(name, lang, versionId)`.
     * The real implementation is a stub, so we compute it ourselves.
     */
    private fun generateId(name: String, lang: String, versionId: Int): Long {
        // The exact value doesn't matter for tests — only consistency does.
        val prime = 31L
        var hash = 0L
        hash = hash * prime + name.hashCode()
        hash = hash * prime + lang.hashCode()
        hash = hash * prime + versionId
        return hash
    }

    /**
     * Reflectively set a [fieldName] on [target], even if it is `private final`.
     *
     * Uses MethodHandles.privateLookupIn to bypass module restrictions (Java 12+).
     * Falls back to standard reflection with setAccessible if that fails.
     */
    internal fun setField(target: Any, fieldName: String, value: Any?) {
        // Find field in the class hierarchy (could be in superclass)
        var current: Class<*>? = target.javaClass
        var field: Field? = null
        while (current != null && field == null) {
            try {
                field = current.getDeclaredField(fieldName)
            } catch (_: NoSuchFieldException) {
                current = current.superclass
            }
        }
        if (field == null) {
            throw NoSuchFieldException("Field '$fieldName' not found in ${target.javaClass.name} or its superclasses")
        }

        // Try MethodHandles.privateLookupIn first (bypasses module restrictions)
        try {
            val lookup = MethodHandles.privateLookupIn(field.declaringClass, MethodHandles.lookup())
            val setter = lookup.unreflectSetter(field)
            setter.invoke(target, value)
            return
        } catch (e: Exception) {
            // If privateLookupIn fails for any reason, fall back
        }

        // Fallback: standard reflection with setAccessible
        try {
            field.isAccessible = true
            field.set(target, value)
        } catch (e: IllegalAccessException) {
            // As last resort, try to remove final modifier via reflection
            // (only works on some JVMs, but worth trying)
            try {
                val modifiersField = Field::class.java.getDeclaredField("modifiers")
                modifiersField.isAccessible = true
                modifiersField.setInt(field, field.modifiers and Modifier.FINAL.inv())
                field.set(target, value)
            } catch (_: Exception) {
                throw e
            }
        }
    }
}
