#!/usr/bin/env python3
"""Build the release packages from the single shared skill source.

Usage:
    python3 scripts/build_releases.py               # validate, build into dist/, verify
    python3 scripts/build_releases.py --out DIR     # build somewhere else

Outputs (VERSION from the VERSION file):
    reloopit-skill-v<VERSION>.zip        reloopit/ skill folder for Claude custom-skill upload
    reloopit-codex-v<VERSION>.zip        Codex local marketplace + Agent Plugins package
    reloopit-claude-code-v<VERSION>.zip  Claude Code local marketplace + plugin
    SHA256SUMS.txt

Archives are reproducible: entries are sorted, timestamps fixed and
permissions normalised, so identical sources give byte-identical ZIPs.
"""

import argparse
import hashlib
import io
import json
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate  # noqa: E402

ROOT = validate.ROOT
SKILL_DIR = validate.SKILL_DIR
SKILL = validate.SKILL_NAME
PLUGIN = validate.PLUGIN_NAME
FIXED_DATE = (1980, 1, 1, 0, 0, 0)
JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
JUNK_SUFFIXES = {".pyc", ".swp", ".tmp", ".bak", ".orig"}


def archive_names(version):
    return {
        "skill": f"{PLUGIN}-skill-v{version}.zip",
        "codex": f"{PLUGIN}-codex-v{version}.zip",
        "claude-code": f"{PLUGIN}-claude-code-v{version}.zip",
    }


def skill_files():
    """Map relative path -> bytes for every file of the shared skill."""
    files = {}
    for path in sorted(SKILL_DIR.rglob("*")):
        rel = path.relative_to(SKILL_DIR).as_posix()
        if path.is_symlink():
            raise SystemExit(f"refusing to package symlink: {rel}")
        if not path.is_file() or path.name in validate.OS_METADATA_NAMES:
            continue  # OS metadata such as .DS_Store is gitignored and never packaged
        if path.suffix in JUNK_SUFFIXES or "__pycache__" in rel:
            raise SystemExit(f"refusing to package temporary file: {rel} (delete it first)")
        files[rel] = path.read_bytes()
    return files


def json_bytes(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def manifest(rel, version):
    data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    # Put version right after name so the manifest reads naturally.
    ordered = {}
    for key, value in data.items():
        ordered[key] = value
        if key == "name":
            ordered["version"] = version
    return json_bytes(ordered)


def text_template(rel, version):
    return (ROOT / rel).read_text(encoding="utf-8").replace("{{VERSION}}", version).encode("utf-8")


def package_contents(version):
    """Return {archive file name: {archive path: bytes}}."""
    skill = skill_files()
    names = archive_names(version)

    skill_zip = {f"{SKILL}/{rel}": data for rel, data in skill.items()}
    # Plugin presentation icons live at the plugin root (./assets/), copied from the skill's own assets.
    icons = {rel: data for rel, data in skill.items() if rel.startswith("assets/")}

    cc_root = f"{PLUGIN}-claude-code-v{version}"
    cc_plugin = f"{cc_root}/plugins/{PLUGIN}"
    claude_code = {
        f"{cc_root}/.claude-plugin/marketplace.json": json_bytes(
            json.loads((ROOT / "packaging/claude-code/marketplace.json").read_text(encoding="utf-8"))),
        f"{cc_root}/INSTALL.md": text_template("packaging/claude-code/INSTALL.md", version),
        f"{cc_plugin}/.claude-plugin/plugin.json": manifest("packaging/claude-code/plugin.json", version),
        **{f"{cc_plugin}/skills/{SKILL}/{rel}": data for rel, data in skill.items()},
        **{f"{cc_plugin}/{rel}": data for rel, data in icons.items()},
    }

    cx_root = f"{PLUGIN}-codex-v{version}"
    cx_plugin = f"{cx_root}/plugins/{PLUGIN}"
    codex = {
        f"{cx_root}/.agents/plugins/marketplace.json": json_bytes(
            json.loads((ROOT / "packaging/codex/marketplace.json").read_text(encoding="utf-8"))),
        f"{cx_root}/INSTALL.md": text_template("packaging/codex/INSTALL.md", version),
        f"{cx_plugin}/plugin.json": manifest("packaging/codex/plugin.json", version),
        **{f"{cx_plugin}/skills/{SKILL}/{rel}": data for rel, data in skill.items()},
        **{f"{cx_plugin}/{rel}": data for rel, data in icons.items()},
    }
    return {names["skill"]: skill_zip, names["codex"]: codex, names["claude-code"]: claude_code}


def write_zip(path, entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3  # unix, so the permission bits below are honoured
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            zf.writestr(info, entries[name], compresslevel=9)
    path.write_bytes(buffer.getvalue())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out_dir, version):
    out_dir.mkdir(parents=True, exist_ok=True)
    built = []
    for name, entries in package_contents(version).items():
        target = out_dir / name
        write_zip(target, entries)
        built.append(target)
    sums = "".join(f"{sha256(p)}  {p.name}\n" for p in sorted(built))
    (out_dir / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")
    return built


# --------------------------------------------------------------------------- verification

def verify_dist(dist_dir, version):
    """Verify every archive independently against the source and the packaging rules."""
    problems = []
    names = archive_names(version)
    expected = package_contents(version)
    sums_path = dist_dir / "SHA256SUMS.txt"
    sums = {}
    if sums_path.is_file():
        for line in sums_path.read_text(encoding="utf-8").splitlines():
            digest, _, fname = line.partition("  ")
            sums[fname] = digest
    else:
        problems.append("SHA256SUMS.txt is missing")

    for kind, fname in names.items():
        path = dist_dir / fname
        if not path.is_file():
            problems.append(f"{fname}: missing")
            continue
        if sums.get(fname) != sha256(path):
            problems.append(f"{fname}: checksum does not match SHA256SUMS.txt")
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            entries = {i.filename: zf.read(i) for i in infos}
            for info in infos:
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    problems.append(f"{fname}: {info.filename} is a symlink")
                if info.filename.startswith("/") or ".." in info.filename.split("/"):
                    problems.append(f"{fname}: unsafe path {info.filename}")
        tops = {n.split("/", 1)[0] for n in entries}
        want_top = SKILL if kind == "skill" else fname[:-4]
        if tops != {want_top}:
            problems.append(f"{fname}: top-level entries must be exactly {want_top}/, found {sorted(tops)}")
        if entries != expected[fname]:
            extra = sorted(set(entries) - set(expected[fname]))
            missing = sorted(set(expected[fname]) - set(entries))
            differ = sorted(n for n in set(entries) & set(expected[fname]) if entries[n] != expected[fname][n])
            problems.append(f"{fname}: does not match shared source (extra={extra}, missing={missing}, differ={differ})")
        for name in entries:
            leaf = name.rsplit("/", 1)[-1]
            if leaf in validate.PRIVATE_NAMES or leaf in JUNK_NAMES or (
                    Path(leaf).suffix.lower() in validate.PRIVATE_SUFFIXES and not validate.is_logo_file(name)):
                problems.append(f"{fname}: excluded file {name}")
            if any(part in ("tests", "docs", ".github", "dist") for part in name.split("/")):
                problems.append(f"{fname}: development-only path {name}")

        # Extract and re-run the skill checks on the packaged copy, independently of the source tree.
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(path) as zf:
                zf.extractall(tmp)
            if kind == "skill":
                skill_dir = Path(tmp) / SKILL
            else:
                skill_dir = Path(tmp) / want_top / "plugins" / PLUGIN / "skills" / SKILL
                problems.extend(f"{fname}: {p}" for p in _verify_plugin(Path(tmp) / want_top, kind, version))
            problems.extend(f"{fname}: {p}" for p in validate.check_skill_dir(skill_dir, version))
    return problems


def _verify_plugin(root, kind, version):
    problems = []
    if kind == "claude-code":
        market_path = root / ".claude-plugin" / "marketplace.json"
        manifest_rel = Path(".claude-plugin") / "plugin.json"
    else:
        market_path = root / ".agents" / "plugins" / "marketplace.json"
        manifest_rel = Path("plugin.json")
    market = json.loads(market_path.read_text(encoding="utf-8"))
    for entry in market["plugins"]:
        source = entry["source"] if isinstance(entry["source"], str) else entry["source"]["path"]
        plugin_dir = (root / source).resolve()
        if root.resolve() not in plugin_dir.parents:
            problems.append(f"marketplace source {source} escapes the package")
            continue
        manifest_path = plugin_dir / manifest_rel
        if not manifest_path.is_file():
            problems.append(f"marketplace source {source} has no {manifest_rel}")
            continue
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if data.get("version") != version or data.get("name") != entry["name"]:
            problems.append(f"{manifest_rel}: name/version mismatch ({data.get('name')}, {data.get('version')})")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()

    if validate.main([]) != 0:
        print("Source validation failed; not building.")
        return 1
    version = validate.read_version()
    out = args.out.resolve()
    built = build(out, version)
    problems = verify_dist(out, version)
    for path in built:
        print(f"built {path.relative_to(out.parent) if out.parent in path.parents else path}  sha256={sha256(path)}")
    print(f"wrote {out / 'SHA256SUMS.txt'}")
    if problems:
        for p in problems:
            print(f"FAIL  {p}")
        return 1
    print("PASS  release archives verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
