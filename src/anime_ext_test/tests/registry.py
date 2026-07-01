"""Abstract base class and registry for extension tests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal

import aiohttp

from anime_ext_test.models import ExtensionMeta, TestResult

if TYPE_CHECKING:
    from anime_ext_test.config import Config

# Global registry of test classes
_TEST_REGISTRY: list[type[ExtensionTest]] = []


class ExtensionTest(ABC):
    """Base class for all extension test categories."""

    name: str = ""  # e.g. "structural"
    category: str = ""  # e.g. "structural"

    def __init__(self, config: Config) -> None:
        self.config = config

    @abstractmethod
    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        """Run all checks for this test category against one extension.

        Args:
            ext: The extension metadata.
            session: An aiohttp session (None for non-HTTP tests like structural).

        Returns:
            List of TestResult instances, one per check.
        """

    def _result(
        self,
        test_name: str,
        status: Literal["pass", "fail", "skip", "error"],
        duration_ms: float = 0.0,
        message: str = "",
        detail: str = "",
    ) -> TestResult:
        """Helper to create a TestResult with the full qualified name."""
        return TestResult(
            test_name=f"{self.category}:{test_name}",
            status=status,
            duration_ms=duration_ms,
            message=message,
            detail=detail,
        )

    def _pass(self, test_name: str, duration_ms: float = 0.0, message: str = "") -> TestResult:
        return self._result(test_name, "pass", duration_ms, message)

    def _fail(self, test_name: str, duration_ms: float = 0.0, message: str = "", detail: str = "") -> TestResult:
        return self._result(test_name, "fail", duration_ms, message, detail)

    def _skip(self, test_name: str, duration_ms: float = 0.0, message: str = "") -> TestResult:
        return self._result(test_name, "skip", duration_ms, message)

    def _error(self, test_name: str, duration_ms: float = 0.0, message: str = "", detail: str = "") -> TestResult:
        return self._result(test_name, "error", duration_ms, message, detail)


def register_test(cls: type[ExtensionTest]) -> type[ExtensionTest]:
    """Decorator to register an ExtensionTest subclass."""
    _TEST_REGISTRY.append(cls)
    return cls


def get_all_tests(config: Config) -> list[ExtensionTest]:
    """Instantiate and return all registered test classes, filtered by config.

    Auto-imports all test modules so that @register_test decorators fire.
    """
    _import_all_test_modules()

    category_filter = set(config.test_categories)
    tests: list[ExtensionTest] = []
    for cls in _TEST_REGISTRY:
        instance = cls(config)
        if not category_filter or instance.category in category_filter:
            tests.append(instance)
    return tests


def _import_all_test_modules() -> None:
    """Import all sibling modules in the tests package to trigger @register_test."""
    import importlib
    import pkgutil

    from anime_ext_test import tests as tests_pkg

    for module_info in pkgutil.iter_modules(tests_pkg.__path__):
        importlib.import_module(f"anime_ext_test.tests.{module_info.name}")
