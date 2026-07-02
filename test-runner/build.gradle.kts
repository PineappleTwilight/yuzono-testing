plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.serialization)
}

android {
    namespace = "keiyoushi.testrunner"

    compileSdk = 34

    buildFeatures {
        resValues = false
    }

    testOptions {
        unitTests.isReturnDefaultValues = true
        unitTests.all {
            it.useJUnitPlatform()
            it.jvmArgs(
                // Allow Unsafe operations (in unnamed module)
                "--add-opens=java.base/sun.misc=ALL-UNNAMED",
                "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
                // Allow reflection on unnamed module packages
                "--add-opens=ALL-UNNAMED/eu.kanade.tachiyomi.animesource.online=ALL-UNNAMED",
                "--add-opens=ALL-UNNAMED/eu.kanade.tachiyomi.network=ALL-UNNAMED",
                "--add-opens=ALL-UNNAMED/eu.kanade.tachiyomi.utils=ALL-UNNAMED",
                "--add-opens=ALL-UNNAMED/eu.kanade.tachiyomi.animesource=ALL-UNNAMED",
                "--add-opens=ALL-UNNAMED/eu.kanade.tachiyomi=ALL-UNNAMED",
            )
        }
    }
}

dependencies {
    implementation(project(":test-framework"))
    // aniyomi-lib (from libs.bundles.common) provides stub classes: AnimeHttpSource, SAnime, SEpisode, etc.
    implementation(libs.bundles.common)

    testImplementation(libs.junit5.api)
    testRuntimeOnly(libs.junit5.engine)
    testRuntimeOnly(libs.junit5.launcher)
    testImplementation(libs.kotest.assertions)
    testImplementation(libs.clikt)
    testImplementation(libs.kotlinx.html)
    testImplementation(libs.mockk)
    testImplementation(libs.coroutines.test)
    testImplementation(libs.kotlin.reflect)
}

tasks.withType<Test> {
    useJUnitPlatform()
}