from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apex_help_is_repository_local() -> None:
    completed = subprocess.run(
        [str(ROOT / "apex"), "help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "External job-app commands fail closed" in completed.stdout


def test_apex_help_survives_unset_home() -> None:
    env = os.environ.copy()
    env.pop("HOME", None)
    env.pop("APEX_JOB_APP_DIR", None)
    completed = subprocess.run(
        [str(ROOT / "apex"), "help"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "Usage: apex" in completed.stdout


def test_missing_external_job_app_dependency_fails_closed(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["APEX_JOB_APP_DIR"] = str(tmp_path)
    completed = subprocess.run(
        [str(ROOT / "apex"), "highway"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 78
    assert "external job-app dependency unavailable" in completed.stderr


def test_installer_places_canonical_dispatcher(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    completed = subprocess.run(
        ["bash", str(ROOT / "install.sh")],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    installed = tmp_path / "bin" / "apex"
    assert installed.is_file()
    assert os.access(installed, os.X_OK)
    help_result = subprocess.run(
        [str(installed), "help"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert help_result.returncode == 0
    assert "Usage: apex" in help_result.stdout


def test_paths_module_honors_explicit_environment_root(tmp_path: Path) -> None:
    base = tmp_path / "base"
    env = os.environ.copy()
    env["APEX_BASE_DIR"] = str(base)
    env["APEX_TASKLET_DIR"] = str(base / "tasklet")
    env["APEX_WORKSPACE_DIR"] = str(base / "workspace")
    env["APEX_TMP_DIR"] = str(base / "tmp")
    env["APEX_CONNECTIONS_FILE"] = str(base / "connections.json")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from core import paths; print(paths.BASE_DIR); print(paths.WORKSPACE_DIR)",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    lines = completed.stdout.strip().splitlines()
    assert lines == [str(base), str(base / "workspace")]


def test_external_casebuild_harness_has_no_implicit_device_paths() -> None:
    source = (ROOT / "tests" / "test_end_to_end_casebuild.py").read_text(
        encoding="utf-8"
    )
    assert "/data/data/com.termux/" not in source
    assert "APEX_CASEBUILDER_ROOT" in source
    assert "APEX_RED_HELIX_ROOT" in source
    assert "TemporaryDirectory" in source
    assert 'if __name__ == "__main__"' in source
