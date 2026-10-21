from pathlib import Path
from unittest.mock import Mock
import re
import tomllib

from scripts.housekeeping import version


def test_project_version_sources_agree_on_the_modernization_prerelease():
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert re.fullmatch(r"2\.0\.0(?:-(?:alpha|beta|rc)\.[1-9][0-9]*)?", project["tool"]["poetry"]["version"])
    assert version.VERSION_NAME == "v" + project["tool"]["poetry"]["version"]
    assert version.SAVE_VERSION_NUMBER == 3


def test_source_build_without_version_ini_uses_commit_metadata(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(version.get_version_info, "instance", None)
    monkeypatch.setattr(version, "find_spec", lambda name: None)
    commit = "1234567890abcdef" * 2 + "12345678"
    monkeypatch.setattr(version.subprocess, "check_output", Mock(return_value=(commit + "\n").encode()))
    info = version.get_version_info()
    assert info.version_number == version.VERSION_NAME + "+" + commit
    assert info.is_source_build and info.git_installed


def test_version_ini_keeps_prerelease_and_existing_channel_independent(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(version.get_version_info, "instance", None)
    monkeypatch.setattr(version, "find_spec", lambda name: None)
    Path("version.ini").write_text("[DEFAULT]\nversion_number=v2.0.0-alpha.1\nrelease_channel=stable\nupstream=kanapuro/kanapuroeditclangen\n", encoding="utf-8")
    info = version.get_version_info()
    assert info.version_number == "v2.0.0-alpha.1"
    assert info.release_channel == "stable" and info.upstream == "kanapuro/kanapuroeditclangen"


def test_development_build_step_writes_semantic_commit_metadata(monkeypatch, tmp_path):
    import subprocess
    import sys

    workflow = Path(".github/workflows/build.yml").read_text(encoding="utf-8")
    command = next(line.strip() for line in workflow.splitlines() if "python -c" in line and "VERSION_NUMBER=" in line)
    commit = "a" * 40
    code = command.removeprefix('python -c "').removesuffix('"').replace("${{ github.sha }}", commit)
    environment = tmp_path / "github_env"
    monkeypatch.setenv("GITHUB_ENV", str(environment))
    subprocess.run([sys.executable, "-c", code], check=True)
    assert environment.read_text().strip() == "VERSION_NUMBER=" + version.VERSION_NAME + "+" + commit
