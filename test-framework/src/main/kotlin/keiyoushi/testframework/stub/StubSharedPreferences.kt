package keiyoushi.testframework.stub

import android.content.SharedPreferences

/**
 * In-memory [SharedPreferences] implementation for JVM unit tests.
 *
 * Supports String, Int, Long, Float, Boolean, and Set<String> types.
 * [Editor.apply] and [Editor.commit] are no-ops that succeed immediately
 * since all data lives in memory.
 */
class StubSharedPreferences : SharedPreferences {

    private val data = mutableMapOf<String, Any?>()

    inner class Editor : SharedPreferences.Editor {
        private val pending = mutableMapOf<String, Any?>()
        private val pendingRemove = mutableSetOf<String>()
        private var clearAll = false

        override fun putString(key: String, value: String?): SharedPreferences.Editor = apply { pending[key] = value }

        override fun putStringSet(key: String, values: Set<String>?): SharedPreferences.Editor = apply { pending[key] = values }

        override fun putInt(key: String, value: Int): SharedPreferences.Editor = apply { pending[key] = value }

        override fun putLong(key: String, value: Long): SharedPreferences.Editor = apply { pending[key] = value }

        override fun putFloat(key: String, value: Float): SharedPreferences.Editor = apply { pending[key] = value }

        override fun putBoolean(key: String, value: Boolean): SharedPreferences.Editor = apply { pending[key] = value }

        override fun remove(key: String): SharedPreferences.Editor = apply { pendingRemove.add(key) }

        override fun clear(): SharedPreferences.Editor = apply { clearAll = true }

        override fun commit(): Boolean {
            applyPending()
            return true
        }

        override fun apply() {
            applyPending()
        }

        private fun applyPending() {
            synchronized(data) {
                if (clearAll) {
                    data.clear()
                    clearAll = false
                }
                for (key in pendingRemove) {
                    data.remove(key)
                }
                pendingRemove.clear()
                data.putAll(pending)
                pending.clear()
            }
        }
    }

    override fun getAll(): Map<String, Any?> = synchronized(data) { data.toMap() }

    override fun getString(key: String, defValue: String?): String? = synchronized(data) { (data[key] as? String?) ?: defValue }

    override fun getStringSet(key: String, defValues: Set<String>?): Set<String>? = synchronized(data) { (data[key] as? Set<String>?) ?: defValues }

    override fun getInt(key: String, defValue: Int): Int = synchronized(data) { (data[key] as? Int) ?: defValue }

    override fun getLong(key: String, defValue: Long): Long = synchronized(data) { (data[key] as? Long) ?: defValue }

    override fun getFloat(key: String, defValue: Float): Float = synchronized(data) { (data[key] as? Float) ?: defValue }

    override fun getBoolean(key: String, defValue: Boolean): Boolean = synchronized(data) { (data[key] as? Boolean) ?: defValue }

    override fun contains(key: String): Boolean = synchronized(data) { data.containsKey(key) }

    override fun edit(): SharedPreferences.Editor = Editor()

    override fun registerOnSharedPreferenceChangeListener(listener: SharedPreferences.OnSharedPreferenceChangeListener) {
        // no-op for tests
    }

    override fun unregisterOnSharedPreferenceChangeListener(listener: SharedPreferences.OnSharedPreferenceChangeListener) {
        // no-op for tests
    }
}
