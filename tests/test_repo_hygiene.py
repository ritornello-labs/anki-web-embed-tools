from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PORTABLE_PATH_MARKERS = (
    "/" + "Users" + "/",
    "/" + "home" + "/",
    "C:" + "\\" + "Users" + "\\",
    "anki-" + "studying",
)

SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".uv-cache",
    ".venv",
    ".venv-apkg",
    "__pycache__",
    "backups",
    "build",
    "coverage",
    "dist",
    "drafts",
    "input",
    "media",
    "node_modules",
    "out",
    "templates",
    "tmp",
}

SKIP_PREFIXES = {
    "data/derived/",
    "data/raw/",
    "polymath/",
}

PORTABLE_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".yaml",
    ".yml",
}


def git_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line]


def is_skipped(path: Path) -> bool:
    as_posix = path.as_posix()
    return bool(SKIP_PARTS.intersection(path.parts)) or any(
        as_posix.startswith(prefix) for prefix in SKIP_PREFIXES
    )


def readable_text(path: Path) -> str | None:
    try:
        return (ROOT / path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


class RepositoryHygieneTest(unittest.TestCase):
    def test_readme_exists(self) -> None:
        self.assertTrue(
            any((ROOT / name).exists() for name in ("README.md", "README.rst", "README")),
            "repository should have a README",
        )

    def test_claude_imports_agents_when_present(self) -> None:
        agents = ROOT / "AGENTS.md"
        if not agents.exists():
            self.skipTest("AGENTS.md is not present")
        claude = ROOT / "CLAUDE.md"
        self.assertTrue(claude.exists(), "CLAUDE.md should exist when AGENTS.md exists")
        self.assertIn("@AGENTS.md", claude.read_text(encoding="utf-8"))

    def test_no_local_workspace_references_in_portable_files(self) -> None:
        offenders: list[str] = []
        for path in git_files():
            if is_skipped(path) or path.suffix not in PORTABLE_SUFFIXES:
                continue
            text = readable_text(path)
            if text is not None and any(
                marker in text for marker in FORBIDDEN_PORTABLE_PATH_MARKERS
            ):
                offenders.append(path.as_posix())

        self.assertEqual([], offenders, "portable files must not reference local workspaces")

    def test_manifest_has_public_release_metadata(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("web_embed_tools", manifest["package"])
        self.assertEqual("0.2.0", manifest["human_version"])
        self.assertEqual(250900, manifest["min_point_version"])
        self.assertEqual(250904, manifest["max_point_version"])
        self.assertNotIn("min_anki_version", manifest)
        self.assertNotIn("max_anki_version", manifest)
        self.assertNotIn("version", manifest)

    def test_release_archive_contains_only_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive = Path(temporary_directory) / "web_embed_tools.ankiaddon"
            subprocess.run(
                ["bash", "scripts/build_ankiaddon.sh", str(archive)],
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            )
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(
                    {"__init__.py", "manifest.json", "wikipedia_embed_core.py"},
                    set(package.namelist()),
                )
                packaged_manifest = json.loads(package.read("manifest.json"))
                self.assertEqual("web_embed_tools", packaged_manifest["package"])

    def test_gui_smoke_probe_checks_addon_and_hook(self) -> None:
        probe = (ROOT / "tests/gui_smoke/probe_addon/__init__.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('ADDON_MODULE = "web_embed_tools"', probe)
        self.assertIn("editor_will_show_context_menu", probe)

    def test_tracked_json_files_parse(self) -> None:
        for path in git_files():
            if is_skipped(path) or path.suffix != ".json":
                continue
            with self.subTest(path=path.as_posix()):
                text = readable_text(path)
                if text is None:
                    self.skipTest(f"{path} is not UTF-8 text")
                json.loads(text)

    def test_tracked_python_files_compile(self) -> None:
        for path in git_files():
            if is_skipped(path) or path.suffix != ".py":
                continue
            with self.subTest(path=path.as_posix()):
                py_compile.compile(str(ROOT / path), doraise=True)


def run_path_check() -> int:
    suite = unittest.TestSuite()
    suite.addTest(
        RepositoryHygieneTest("test_no_local_workspace_references_in_portable_files")
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--path-only"]:
        raise SystemExit(run_path_check())
    unittest.main()
