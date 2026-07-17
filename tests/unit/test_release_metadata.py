"""Public release metadata and integration-resource checks."""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path
from urllib.parse import unquote

from vaydeer_studio import __version__
from vaydeer_studio.cli.main import build_parser

ROOT = Path(__file__).resolve().parents[2]


def test_release_version_and_urls_are_consistent() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert metadata["version"] == __version__ == "1.0.2"
    assert metadata["urls"]["Repository"] == "https://github.com/callum-baillie/vaydeer-studio-linux"
    assert "--version" in build_parser().format_help()

    bootstrap_bytes = (ROOT / "scripts/bootstrap.sh").read_bytes()
    bootstrap = bootstrap_bytes.decode("utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert 'readonly STUDIO_VERSION="1.0.2"' in bootstrap
    assert "/releases/download/v${STUDIO_VERSION}" in bootstrap
    assert "UV_INSTALLER_SHA256=" in bootstrap
    assert "/v1.0.2/scripts/bootstrap.sh" in readme
    assert hashlib.sha256(bootstrap_bytes).hexdigest() in readme


def test_host_integration_is_scoped_and_distribution_neutral() -> None:
    rule = (ROOT / "packaging/udev/99-vaydeer-studio.rules").read_text(encoding="utf-8")
    assert 'MODE="0660"' in rule
    assert 'TAG+="uaccess"' in rule
    assert 'ENV{DEVPATH}=="*:1.0/*"' in rule
    assert 'ENV{DEVPATH}=="*:1.2/*"' in rule
    assert "0666" not in rule
    assert "GROUP=" not in rule

    service = (ROOT / "packaging/systemd/vaydeer-studio.service").read_text(encoding="utf-8")
    assert "NoNewPrivileges=true" in service
    assert "Restart=on-failure" in service


def test_relative_markdown_links_resolve() -> None:
    link_pattern = re.compile(r"!?(?:\[[^]]*])\(([^)]+)\)")
    failures: list[str] = []
    markdown_files = [
        *ROOT.glob("*.md"),
        *ROOT.joinpath("docs").rglob("*.md"),
        *ROOT.joinpath("packaging").glob("*.md"),
        *ROOT.joinpath("research").rglob("*.md"),
    ]
    for markdown in markdown_files:
        for target in link_pattern.findall(markdown.read_text(encoding="utf-8")):
            target = target.strip().strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "#")):
                continue
            resolved = (markdown.parent / unquote(target)).resolve()
            if not resolved.exists():
                failures.append(f"{markdown.relative_to(ROOT)} -> {target}")
    assert failures == []
