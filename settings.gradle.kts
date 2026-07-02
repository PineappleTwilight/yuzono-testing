@file:Suppress("ktlint:standard:kdoc")

pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
        maven(url = "https://www.jitpack.io")
    }
}

dependencyResolutionManagement {
    @Suppress("UnstableApiUsage")
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    @Suppress("UnstableApiUsage")
    repositories {
        google()
        mavenCentral()
        maven(url = "https://www.jitpack.io")
    }
}

enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")

rootProject.name = "anime-extensions-testing"

// Note: repo/ is a git submodule (anime-extensions) - it's built separately
// The test-runner dynamically discovers extensions from the repo/ directory

// Include test modules
include(":test-runner")
include(":test-framework")