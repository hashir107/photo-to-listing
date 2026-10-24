"""Release packaging tests: contents, independence, reproducibility, tamper detection."""

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_releases  # noqa: E402
import validate  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.version = validate.read_version()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "dist"
        cls.built = build_releases.build(cls.out, cls.version)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_three_archives_and_checksums(self):
        names = sorted(p.name for p in self.out.iterdir())
        expected = sorted(list(build_releases.archive_names(self.version).values()) + ["SHA256SUMS.txt"])
        self.assertEqual(names, expected)

    def test_archives_verify(self):
        self.assertEqual(build_releases.verify_dist(self.out, self.version), [])

    def test_skill_zip_has_skill_folder_at_top_level(self):
        path = self.out / build_releases.archive_names(self.version)["skill"]
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        self.assertIn("reloopit/SKILL.md", names)
        self.assertTrue(all(n.startswith("reloopit/") for n in names))

    def test_manifests_carry_release_version(self):
        names = build_releases.archive_names(self.version)
        with zipfile.ZipFile(self.out / names["claude-code"]) as zf:
            root = names["claude-code"][:-4]
            cc = json.loads(zf.read(f"{root}/plugins/reloopit/.claude-plugin/plugin.json"))
        with zipfile.ZipFile(self.out / names["codex"]) as zf:
            root = names["codex"][:-4]
            cx = json.loads(zf.read(f"{root}/plugins/reloopit/plugin.json"))
        self.assertEqual(cc["version"], self.version)
        self.assertEqual(cx["version"], self.version)
        self.assertEqual(list(cx)[:3], ["$schema", "name", "version"])

    def test_shared_skill_identical_in_every_package(self):
        source = {rel: data for rel, data in build_releases.skill_files().items()}
        contents = build_releases.package_contents(self.version)
        for archive, entries in contents.items():
            # Skill files sit at reloopit/… in the skill ZIP and at …/skills/reloopit/… in plugin packages.
            packaged = {}
            for name, data in entries.items():
                if "/skills/reloopit/" in name:
                    packaged[name.split("/skills/reloopit/", 1)[1]] = data
                elif name.startswith("reloopit/"):
                    packaged[name.removeprefix("reloopit/")] = data
            self.assertEqual(packaged, source, archive)

    def test_plugin_packages_carry_root_icons(self):
        contents = build_releases.package_contents(self.version)
        names = build_releases.archive_names(self.version)
        for kind in ("codex", "claude-code"):
            root = names[kind][:-4]
            for icon in ("logo.png", "icon-small.png"):
                self.assertIn(f"{root}/plugins/reloopit/assets/{icon}", contents[names[kind]])

    def test_build_is_reproducible(self):
        with tempfile.TemporaryDirectory() as other:
            again = build_releases.build(Path(other), self.version)
            self.assertEqual([digest(p) for p in again], [digest(p) for p in self.built])

    def test_tampered_archive_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build_releases.build(out, self.version)
            target = out / build_releases.archive_names(self.version)["skill"]
            with zipfile.ZipFile(target, "a") as zf:
                zf.writestr("reloopit/notes.txt", "stray file")
            problems = build_releases.verify_dist(out, self.version)
            self.assertTrue(any("checksum" in p for p in problems))
            self.assertTrue(any("does not match shared source" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
