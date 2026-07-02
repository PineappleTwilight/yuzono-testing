package keiyoushi.testrunner.tests

import keiyoushi.testframework.model.ExtensionMeta
import keiyoushi.testrunner.model.TestResult
import java.io.File

/**
 * Structural tests - validate build.gradle metadata without HTTP.
 * Mirrors Python's structural.py (10 checks).
 */
@RegisterTest
class StructuralTest(config: TestConfig) : ExtensionTest(config) {

    override val name = "structural"
    override val category = "structural"

    override fun run(ext: ExtensionMeta): List<TestResult> {
        val repoDir = getRepoDir(ext)
        val results = mutableListOf<TestResult>()

        results.add(testExtNamePresent(ext))
        results.add(testExtClassFormat(ext))
        results.add(testExtVersionCodePositive(ext))
        results.add(testExtClassExists(ext, repoDir))
        results.add(testBaseUrlValid(ext))
        results.add(testThemePkgExists(ext, repoDir))
        results.add(testOverrideVersionCode(ext))
        results.add(testBuildGradleParseable(ext))
        results.add(testPackageStructure(ext, repoDir))
        results.add(testFactoryClassConsistency(ext, repoDir))

        return results
    }

    private fun getRepoDir(ext: ExtensionMeta): File {
        val buildGradle = File(ext.buildGradlePath)
        return buildGradle.parentFile.parentFile.parentFile
    }

    private fun testExtNamePresent(ext: ExtensionMeta): TestResult = if (ext.extName.isNotBlank()) {
        pass("ext_name_present", message = "extName='${ext.extName}'")
    } else {
        fail("ext_name_present", message = "extName is empty or missing")
    }

    private fun testExtClassFormat(ext: ExtensionMeta): TestResult = if (ext.extClass.startsWith(".")) {
        pass("ext_class_format", message = "extClass='${ext.extClass}'")
    } else {
        fail("ext_class_format", message = "extClass must start with '.', got '${ext.extClass}'")
    }

    private fun testExtVersionCodePositive(ext: ExtensionMeta): TestResult = when {
        ext.extVersionCode > 0 -> {
            pass("ext_version_code_positive", message = "extVersionCode=${ext.extVersionCode}")
        }
        ext.overrideVersionCode >= 0 -> {
            skip("ext_version_code_positive", message = "extVersionCode=0 with overrideVersionCode=${ext.overrideVersionCode}")
        }
        else -> {
            fail("ext_version_code_positive", message = "extVersionCode must be > 0, got ${ext.extVersionCode}")
        }
    }

    private fun testExtClassExists(ext: ExtensionMeta, repoDir: File): TestResult {
        val classFile = resolveClassFile(ext, repoDir)
        if (classFile != null && classFile.isFile) {
            return pass("ext_class_exists", message = "Found: ${classFile.relativeTo(repoDir)}")
        }

        // Fallback: search anywhere under src/{lang}/{name}/ for the class file
        val fallback = findClassFileByRglob(ext, repoDir)
        if (fallback != null) {
            return pass("ext_class_exists", message = "Found (non-standard path): ${fallback.relativeTo(repoDir)}")
        }

        return fail(
            "ext_class_exists",
            message = "Class file not found for extClass='${ext.extClass}'",
            detail = "Expected near: src/${ext.lang}/${ext.name}/src/",
        )
    }

    private fun testBaseUrlValid(ext: ExtensionMeta): TestResult = when {
        ext.baseUrl.isBlank() -> skip("base_url_valid", message = "No baseUrl in build.gradle")
        ext.baseUrl.startsWith("http://") || ext.baseUrl.startsWith("https://") -> {
            pass("base_url_valid", message = "baseUrl='${ext.baseUrl}'")
        }
        else -> {
            fail("base_url_valid", message = "baseUrl must start with http:// or https://, got '${ext.baseUrl}'")
        }
    }

    private fun testThemePkgExists(ext: ExtensionMeta, repoDir: File): TestResult {
        if (!ext.isMultisrc) {
            return skip("theme_pkg_exists", message = "Not a multisrc extension")
        }

        val themePkg = ext.themePkg ?: ""
        val themeDir = File(repoDir, "lib-multisrc/$themePkg")
        return if (themeDir.isDirectory) {
            pass("theme_pkg_exists", message = "lib-multisrc/$themePkg/ exists")
        } else {
            fail("theme_pkg_exists", message = "lib-multisrc/$themePkg/ directory does not exist")
        }
    }

    private fun testOverrideVersionCode(ext: ExtensionMeta): TestResult = if (ext.overrideVersionCode >= 0) {
        pass("override_version_code_valid", message = "overrideVersionCode=${ext.overrideVersionCode}")
    } else {
        fail("override_version_code_valid", message = "overrideVersionCode must be >= 0, got ${ext.overrideVersionCode}")
    }

    private fun testBuildGradleParseable(ext: ExtensionMeta): TestResult = if (ext.extName.isNotBlank() && ext.extClass.isNotBlank()) {
        pass("build_gradle_parseable", message = "ext block parsed successfully")
    } else {
        fail("build_gradle_parseable", message = "ext block could not be fully parsed")
    }

    private fun testPackageStructure(ext: ExtensionMeta, repoDir: File): TestResult {
        val pkgDir = File(repoDir, "src/${ext.lang}/${ext.name}/src/eu/kanade/tachiyomi/animeextension/${ext.lang}/${ext.name}")
        if (pkgDir.isDirectory) {
            val ktFiles = pkgDir.listFiles { _, name -> name.endsWith(".kt") }
            if (!ktFiles.isNullOrEmpty()) {
                return pass("package_structure", message = "Found ${ktFiles.size} .kt file(s) in expected package dir")
            }
        }

        val srcDir = File(repoDir, "src/${ext.lang}/${ext.name}/src")
        if (srcDir.isDirectory) {
            val ktFiles = srcDir.walkTopDown().filter { it.extension == "kt" }.toList()
            if (ktFiles.isNotEmpty()) {
                return pass("package_structure", message = "Found ${ktFiles.size} .kt file(s) under src/")
            }
        }

        return fail("package_structure", message = "Expected package directory not found: $pkgDir")
    }

    private fun testFactoryClassConsistency(ext: ExtensionMeta, repoDir: File): TestResult {
        if (!ext.extClass.contains("Factory")) {
            return skip("factory_class_consistency", message = "Not a factory extension")
        }

        val baseClass = ext.extClass.replace("Factory", "")
        val baseMeta = ext.copy(extClass = baseClass)
        val classFile = resolveClassFile(baseMeta, repoDir)

        return if (classFile != null && classFile.isFile) {
            pass("factory_class_consistency", message = "Factory base class '$baseClass' exists")
        } else {
            fail("factory_class_consistency", message = "Factory base class '$baseClass' not found")
        }
    }

    private fun resolveClassFile(ext: ExtensionMeta, repoDir: File): File? {
        val className = ext.extClass.trimStart('.')
        if (className.isBlank()) return null

        val pkgDir = File(repoDir, "src/${ext.lang}/${ext.name}/src/eu/kanade/tachiyomi/animeextension/${ext.lang}/${ext.name}")
        return File(pkgDir, "$className.kt")
    }

    private fun findClassFileByRglob(ext: ExtensionMeta, repoDir: File): File? {
        val className = ext.extClass.trimStart('.')
        if (className.isBlank()) return null

        val extSrc = File(repoDir, "src/${ext.lang}/${ext.name}/src")
        if (!extSrc.isDirectory) return null

        return extSrc.walkTopDown()
            .filter { it.name == "$className.kt" }
            .firstOrNull()
    }
}
