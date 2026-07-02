package keiyoushi.testframework.bootstrap

import android.app.Application
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import keiyoushi.testframework.stub.StubApplication
import kotlinx.serialization.json.Json
import uy.kohesive.injekt.Injekt
import uy.kohesive.injekt.api.addSingleton
import uy.kohesive.injekt.api.get

/**
 * Bootstraps the Injekt dependency graph for JVM unit tests.
 *
 * The aniyomi-lib JAR ships as API stubs — every constructor throws
 * `Exception("Stub!")`. That means [AnimeHttpSource] cannot be instantiated
 * normally; [SourceInstantiator] uses `sun.misc.Unsafe` to bypass the stub
 * constructor and then injects the `network`/`client`/`headers`/`id` fields
 * via reflection.
 *
 * Call [setUp] once before any test that needs extension classes.
 * It is idempotent — repeated calls are no-ops.
 */
object TestBootstrap {

    @Volatile
    private var isSetUp = false

    private val lock = Any()

    /**
     * Populate the Injekt graph with the minimum singletons required
     * by [keiyoushi.utils.Source] and its subclasses:
     *
     * - [Application] → [StubApplication]
     * - [Json] → `Json { ignoreUnknownKeys = true }`
     */
    fun setUp() {
        synchronized(lock) {
            if (isSetUp) return
            Injekt.addSingleton<Application>(StubApplication())
            Injekt.addSingleton(Json { ignoreUnknownKeys = true })
            isSetUp = true
        }
    }

    /** Whether [setUp] has been called in this JVM process. */
    val isInitialized: Boolean get() = isSetUp

    /**
     * Return the [StubApplication] registered with Injekt.
     * Throws [IllegalStateException] if [setUp] has not been called.
     */
    val application: StubApplication
        get() {
            check(isSetUp) { "TestBootstrap.setUp() has not been called" }
            return Injekt.get<Application>() as StubApplication
        }
}
