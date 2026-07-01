"""Parallel test orchestrator — runs all registered tests across extensions."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

import aiohttp

from anime_ext_test.config import Config
from anime_ext_test.discovery import discover_extensions, filter_extensions, get_repo_commit
from anime_ext_test.http_client import create_session
from anime_ext_test.models import ExtensionReport, RunReport, TestResult
from anime_ext_test.tests.registry import get_all_tests

logger = logging.getLogger(__name__)


async def run_all_tests(config: Config) -> RunReport:
    """Main entry point: discover extensions, run all tests, return report."""
    report = RunReport(
        run_id=uuid.uuid4().hex[:12],
        started_at=datetime.now(UTC),
        repo_url=config.repo_url,
    )

    # Discover extensions
    from pathlib import Path

    from anime_ext_test.discovery import clone_repo

    repo_dir = Path(config.repo_dir) if config.no_clone and config.repo_dir else clone_repo(config)

    report.repo_commit = get_repo_commit(repo_dir)

    logger.info("Discovering extensions in %s", repo_dir)
    all_extensions = discover_extensions(repo_dir)
    logger.info("Discovered %d extensions", len(all_extensions))

    extensions = filter_extensions(all_extensions, config)
    logger.info(
        "After filtering: %d extensions (languages=%s, skip_api_key=%s)",
        len(extensions),
        config.languages or "all",
        config.skip_api_key_extensions,
    )

    # Instantiate test classes
    test_instances = get_all_tests(config)
    logger.info("Running %d test categories: %s", len(test_instances), [t.name for t in test_instances])

    # Run all extensions with bounded concurrency
    session = create_session(config)
    try:
        semaphore = asyncio.Semaphore(config.max_concurrent)

        async def run_extension(ext) -> ExtensionReport:
            async with semaphore:
                return await _run_extension_tests(ext, test_instances, session, config)

        tasks = [run_extension(ext) for ext in extensions]
        ext_reports = await asyncio.gather(*tasks, return_exceptions=False)
    finally:
        await session.close()

    report.extensions = ext_reports
    report.finished_at = datetime.now(UTC)

    logger.info(
        "Run complete: %d extensions tested in %.1fs",
        len(ext_reports),
        (report.finished_at - report.started_at).total_seconds(),
    )

    return report


async def _run_extension_tests(
    ext,
    test_instances: list,
    session: aiohttp.ClientSession,
    config: Config,
) -> ExtensionReport:
    """Run all test categories against a single extension."""
    ext_report = ExtensionReport(extension=ext)

    for test_instance in test_instances:
        try:
            if test_instance.category == "structural":
                results = await asyncio.wait_for(
                    test_instance.run(ext),
                    timeout=config.http_total_timeout,
                )
            else:
                results = await asyncio.wait_for(
                    test_instance.run(ext, session),
                    timeout=config.http_total_timeout,
                )
        except TimeoutError:
            results = [TestResult(
                test_name=f"{test_instance.category}:timeout",
                status="error",
                message=f"Test category timed out after {config.http_total_timeout}s",
            )]
        except Exception as exc:
            results = [TestResult(
                test_name=f"{test_instance.category}:unexpected_error",
                status="error",
                message=f"Unexpected error: {exc}",
            )]
        ext_report.results.extend(results)

    ext_report.finished_at = datetime.now(UTC)

    # Log summary per extension
    p = ext_report.passed
    f = ext_report.failed
    s = ext_report.skipped
    e = ext_report.errored
    logger.info("%s: %d pass, %d fail, %d skip, %d error", ext.module_id, p, f, s, e)

    return ext_report
