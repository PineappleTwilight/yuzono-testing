package keiyoushi.testframework.stub

import android.app.Application
import android.content.SharedPreferences
import android.content.res.Resources

/**
 * Minimal [Application] stub for JVM unit tests.
 *
 * Returns [StubSharedPreferences] from [getSharedPreferences] so that
 * extension classes using `getPreferencesLazy` work without Android framework.
 * All other Android Application methods return defaults (thanks to
 * `unitTests.isReturnDefaultValues = true` in the test-framework build config).
 */
class StubApplication : Application() {

    private val prefsMap = mutableMapOf<String, SharedPreferences>()

    override fun getSharedPreferences(name: String?, mode: Int): SharedPreferences = prefsMap.getOrPut(name ?: "default") { StubSharedPreferences() }

    // Provide a no-op Resources to avoid Android framework crashes
    override fun getResources(): Resources = Resources.getSystem()
}
