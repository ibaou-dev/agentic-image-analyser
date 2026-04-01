"""Unit tests for the precheck module."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from agentic_vision.precheck import (
    CheckResult,
    all_passed,
    check_auth_available,
    check_cli_installed,
    check_python_version,
    check_uv_available,
    run_all_checks,
)


class TestCheckResults:
    def test_all_passed_true(self) -> None:
        results = [CheckResult("a", True, "ok"), CheckResult("b", True, "ok")]
        assert all_passed(results) is True

    def test_all_passed_false_if_any_fails(self) -> None:
        results = [CheckResult("a", True, "ok"), CheckResult("b", False, "nope")]
        assert all_passed(results) is False


class TestPythonVersionCheck:
    def test_current_python_passes(self) -> None:
        # We're running 3.12+, so this should pass
        result = check_python_version()
        assert result.passed is True

    def test_old_python_fails(self) -> None:
        with patch.object(sys, "version_info", (3, 10, 0, "final", 0)):
            result = check_python_version()
            assert result.passed is False
            assert result.actionable  # has fix instructions


class TestUvCheck:
    def test_uv_found(self) -> None:
        # uv is installed in this environment
        result = check_uv_available()
        assert result.passed is True

    def test_uv_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            result = check_uv_available()
            assert result.passed is False
            assert "uv" in result.actionable.lower()


class TestCliInstalledCheck:
    def test_found_when_on_path(self) -> None:
        with patch(
            "agentic_vision.precheck.shutil.which",
            return_value="/home/user/.local/bin/agentic-vision",
        ):
            result = check_cli_installed()
        assert result.passed is True
        assert "/home/user/.local/bin/agentic-vision" in result.message

    def test_not_found_when_absent(self) -> None:
        with patch("agentic_vision.precheck.shutil.which", return_value=None):
            result = check_cli_installed()
        assert result.passed is False
        assert "uv tool install" in result.actionable


class TestAuthCheck:
    def test_passes_when_oauth_creds_exist(self, tmp_path: Path) -> None:
        creds = tmp_path / ".gemini" / "oauth_creds.json"
        creds.parent.mkdir()
        creds.write_text("{}")
        with patch("agentic_vision.precheck.Path.home", return_value=tmp_path):
            result = check_auth_available()
        assert result.passed is True

    def test_passes_when_env_var_set(self, tmp_path: Path) -> None:
        import os

        with (
            patch("agentic_vision.precheck.Path.home", return_value=tmp_path),
            patch.dict(os.environ, {"GEMINI_API_KEY": "AIza-test"}),
        ):
            result = check_auth_available()
            assert result.passed is True

    def test_fails_when_nothing_configured(self, tmp_path: Path) -> None:
        import os

        with (
            patch("agentic_vision.precheck.Path.home", return_value=tmp_path),
            patch.dict(
                os.environ,
                {
                    "GEMINI_API_KEY": "",
                    "OPENAI_API_KEY": "",
                    "ANTHROPIC_API_KEY": "",
                },
            ),
        ):
            result = check_auth_available()
            assert result.passed is False
            assert result.actionable


class TestRunAllChecks:
    def test_returns_list_of_check_results(self) -> None:
        results = run_all_checks()
        assert len(results) >= 4
        assert all(isinstance(r, CheckResult) for r in results)
        assert all(hasattr(r, "name") and hasattr(r, "passed") for r in results)
