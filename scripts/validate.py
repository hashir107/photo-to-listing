#!/usr/bin/env python3
"""Validate the photo-to-listing repository: skill format, schema, examples,
packaging configuration, version consistency and private-file hygiene.

Usage:
    python3 scripts/validate.py              # source checks
    python3 scripts/validate.py --dist dist  # also verify built release archives
    python3 scripts/validate.py --external   # also run skills-ref if installed
    python3 scripts/validate.py --output out.json  # check one model-produced metadata document

Only the Python standard library is required. If `jsonschema` is installed,
schema and example validation is cross-checked with it as well.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import minischema  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "reloop"
PLUGIN_NAME = "photo-to-listing"
SKILL_DIR = ROOT / "skills" / SKILL_NAME
DIALECT = "https://json-schema.org/draft/2020-12/schema"

SPEC_FRONTMATTER_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
# Bundled resource references inside skill Markdown: `references/x.md`, (examples/y.json), schema.json
RESOURCE_REF_RE = re.compile(r"(?<![\w/.-])((?:references|examples|scripts|assets)/[\w./-]+|schema\.json)")

# Listing-copy policy: things ReLoop must never add on its own.
LISTING_FORBIDDEN = [
    (re.compile(r"€|\bEUR\b|\bVB\b|Festpreis|\bPreis\b|\bprice\b", re.I), "price or negotiation term"),
    (re.compile(r"Garantie|Gewährleistung|warranty|guarantee", re.I), "warranty claim"),
    (re.compile(r"Privatverkauf|private sale|keine Rücknahme", re.I), "seller-status or legal disclaimer"),
    (re.compile(r"wie neu|like new|neuwertig|top[- ]?zustand|mint condition", re.I), "unsupported hype"),
    (re.compile(r"S/N|Seriennummer|serial number|IMEI", re.I), "serial identifier"),
    (re.compile(r"Versand|Abholung|shipping|pick-?up", re.I), "shipping or pickup arrangement"),
    (re.compile(r"https?://", re.I), "URL"),
]

PLACEHOLDERS = {"unknown", "unbekannt", "n/a", "na", "none", "null", "-", "?", "tbd"}

SECRET_PATTERNS = [
    (re.compile(r"sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"), "API key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "GitHub token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"X-Amz-Signature=|[?&](?:sig|signature|token)=[A-Za-z0-9%]{16,}", re.I), "signed URL"),
]
PRIVATE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".tif", ".tiff",
                    ".mov", ".mp4", ".pem", ".key", ".p12", ".env"}
PRIVATE_NAMES = {".env", "id_rsa", "id_ed25519", ".netrc", "credentials.json"}
SCAN_SKIP_DIRS = {".git", "dist", "__pycache__", ".venv", "venv", "node_modules"}


class Report:
    def __init__(self):
        self.errors = []
        self.passed = []

    def check(self, label, problems):
        if problems:
            self.errors.extend(f"[{label}] {p}" for p in problems)
        else:
            self.passed.append(label)

    def ok(self):
        return not self.errors


# --------------------------------------------------------------------------- SKILL.md

def parse_frontmatter(text):
    """Parse the YAML subset used in SKILL.md frontmatter (scalars and one nested map).

    Raises ValueError for constructs outside that subset, so ambiguous YAML is
    caught instead of being parsed differently by different hosts.
    """
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with '---' frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("frontmatter is not closed with '---'")
    block, body = text[4:end], text[end + 5:]
    data, current_map = {}, None
    for lineno, line in enumerate(block.split("\n"), start=2):
        if not line.strip():
            continue
        if "\t" in line:
            raise ValueError(f"line {lineno}: tabs are not allowed")
        indented = line.startswith("  ")
        match = re.match(r"^\s*([A-Za-z0-9_-]+):(?: (.*))?$", line)
        if not match:
            raise ValueError(f"line {lineno}: expected 'key: value'")
        key, raw = match.group(1), match.group(2)
        if indented:
            if current_map is None:
                raise ValueError(f"line {lineno}: unexpected indentation")
            current_map[key] = _scalar(raw, lineno)
            continue
        if raw is None or raw == "":
            current_map = data[key] = {}
        else:
            current_map = None
            data[key] = _scalar(raw, lineno)
    return data, body


def _scalar(raw, lineno):
    if raw is None:
        raise ValueError(f"line {lineno}: missing value")
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    if ": " in raw or " #" in raw or raw[0] in "[{&*!|>%@`\"'":
        raise ValueError(f"line {lineno}: value needs quoting to be unambiguous YAML: {raw[:40]!r}")
    return raw


def check_skill_dir(skill_dir, expected_version=None):
    """Spec checks for one skill directory. Used for the source and for each archive."""
    problems = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_md}: missing"]
    text = skill_md.read_text(encoding="utf-8")
    try:
        meta, body = parse_frontmatter(text)
    except ValueError as exc:
        return [f"SKILL.md frontmatter: {exc}"]

    unknown = set(meta) - SPEC_FRONTMATTER_KEYS
    if unknown:
        problems.append(f"frontmatter keys not in the Agent Skills spec: {sorted(unknown)}")
    name = meta.get("name")
    if not isinstance(name, str) or not (1 <= len(name) <= 64) or not NAME_RE.match(name):
        problems.append(f"name {name!r} violates the spec (lowercase a-z, 0-9, single hyphens, 1-64 chars)")
    if name != skill_dir.name:
        problems.append(f"name {name!r} must match directory name {skill_dir.name!r}")
    desc = meta.get("description")
    if not isinstance(desc, str) or not (1 <= len(desc) <= 1024):
        problems.append("description must be 1-1024 characters")
    comp = meta.get("compatibility")
    if comp is not None and (not isinstance(comp, str) or not (1 <= len(comp) <= 500)):
        problems.append("compatibility must be 1-500 characters")
    metadata = meta.get("metadata", {})
    if not isinstance(metadata, dict) or not all(isinstance(v, str) for v in metadata.values()):
        problems.append("metadata must map strings to strings")
    if expected_version and metadata.get("version") != expected_version:
        problems.append(f"metadata.version {metadata.get('version')!r} != VERSION {expected_version!r}")
    if not body.strip():
        problems.append("SKILL.md body is empty")
    if text.count("\n") > 500:
        problems.append("SKILL.md exceeds the recommended 500 lines")

    # Resource references must be relative, present and inside the skill.
    referenced = set()
    for md in [skill_md, *sorted(skill_dir.glob("references/*.md"))]:
        content = md.read_text(encoding="utf-8")
        for ref in RESOURCE_REF_RE.findall(content):
            ref = ref.rstrip(".")
            if ref.endswith("/"):
                continue
            referenced.add(ref)
            if not (skill_dir / ref).is_file():
                problems.append(f"{md.name}: referenced resource {ref!r} does not exist")
        if re.search(r"(?<![\w.])\.\./|(?:^|[\s`(])/(?:Users|home|tmp|private)/|[A-Za-z]:\\\\", content):
            problems.append(f"{md.name}: contains a parent-relative or absolute filesystem path")

    files = sorted(p for p in skill_dir.rglob("*") if p.is_file() or p.is_symlink())
    for path in files:
        rel = path.relative_to(skill_dir).as_posix()
        if path.is_symlink():
            problems.append(f"{rel}: symlinks are not allowed in the skill")
        if rel != "SKILL.md" and not rel.startswith("references/") and rel not in referenced:
            problems.append(f"{rel}: bundled file is not referenced from SKILL.md")
    return problems


# --------------------------------------------------------------------------- schema and examples

def load_schema():
    return json.loads((SKILL_DIR / "schema.json").read_text(encoding="utf-8"))


def check_schema_file(schema):
    problems = []
    if schema.get("$schema") != DIALECT:
        problems.append(f"$schema must declare the 2020-12 dialect ({DIALECT})")
    version = schema.get("properties", {}).get("schema_version", {}).get("const")
    if not version or not SEMVER_RE.match(version):
        problems.append("properties.schema_version must be a semver const")
    elif not str(schema.get("$id", "")).endswith(":" + version):
        problems.append("$id must end with the schema version")
    required = set(schema.get("required", []))
    missing = set(schema.get("properties", {})) - required
    if missing:
        problems.append(f"every top-level field must be required (stable shape): {sorted(missing)}")
    problems.extend(minischema.check_schema(schema))
    try:
        import jsonschema
    except ImportError:
        pass
    else:
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as exc:
            problems.append(f"jsonschema meta-validation: {exc.message}")
    return problems


def _listing_texts(doc):
    en = doc.get("listing_translations", {}).get("en", {})
    return [t for t in (doc.get("listing_title"), doc.get("listing_description"),
                        en.get("title"), en.get("description")) if isinstance(t, str)]


def semantic_errors(doc):
    """Integrity rules that JSON Schema alone cannot express. See references/extraction-rules.md."""
    errors = []
    evidence = doc.get("evidence", [])
    ids = [e["id"] for e in evidence]
    if len(ids) != len(set(ids)):
        errors.append("evidence ids are not unique")
    by_id = {e["id"]: e for e in evidence}
    photos = {p["ref"]: p for p in doc.get("photos", [])}
    inspected = {ref for ref, p in photos.items() if p["inspected"]}

    def refs_in(items, label):
        for i, item in enumerate(items or []):
            for ref in item.get("evidence_refs", []):
                if ref not in by_id:
                    errors.append(f"{label}/{i}: evidence_ref {ref} does not exist")

    for key in ("units", "visible_defects", "included_accessories", "missing_accessories", "attributes"):
        refs_in(doc.get(key), "/" + key)

    for e in evidence:
        where = f"evidence {e['id']}"
        if not minischema.pointer_exists(doc, e["field_path"]):
            errors.append(f"{where}: field_path {e['field_path']} does not resolve")
        if e["photo_ref"] is not None and e["photo_ref"] not in photos:
            errors.append(f"{where}: photo_ref {e['photo_ref']} is not in photos")
        if e["source"] in ("photo", "readable_label") and e["photo_ref"] not in inspected:
            errors.append(f"{where}: {e['source']} evidence needs an inspected photo_ref")
        if (e["source"] == "external_reference") != (e["url"] is not None):
            errors.append(f"{where}: url is required for external_reference and only for it")
        if LISTING_FORBIDDEN[4][0].search(e["observation"]) and "not recorded" not in e["observation"]:
            errors.append(f"{where}: observation appears to contain a serial identifier")

    def evidence_for(path, sources=None, certainty=None):
        return [e for e in evidence if e["field_path"] == path
                and (sources is None or e["source"] in sources)
                and (certainty is None or e["certainty"] == certainty)]

    for field in ("item_name", "item_type", "brand", "model", "suggested_category"):
        if isinstance(doc.get(field), str) and doc[field].strip().lower() in PLACEHOLDERS:
            errors.append(f"/{field} uses placeholder {doc[field]!r}; unknown scalars must be null")
    for field in ("brand", "model"):
        if doc.get(field) is not None and not evidence_for("/" + field, certainty="supported"):
            errors.append(f"/{field} is set without supported evidence")
    for field in ("item_type", "quantity", "physical_condition", "functional_status"):
        if doc.get(field) is not None and not evidence_for("/" + field):
            errors.append(f"/{field} is set without evidence")
    if doc.get("sale_configuration") != "unknown" and not evidence_for("/sale_configuration"):
        errors.append("/sale_configuration is set without evidence")
    if doc.get("functional_status") is not None and not evidence_for(
            "/functional_status", sources={"user_statement", "external_reference"}):
        errors.append("/functional_status needs a user_statement or external_reference; photos alone do not establish function")

    for field in ("functional_status", "physical_condition"):
        if doc.get(field) == "mixed":
            values = {u.get(field) for u in doc.get("units", []) if u.get(field) is not None}
            if len(values) < 2:
                errors.append(f"/{field} is 'mixed' but units do not record differing values")

    if photos and not inspected:
        if doc.get("photo_set_interpretation") != "no_inspectable_photos":
            errors.append("no photo was inspected, so photo_set_interpretation must be no_inspectable_photos")
    if inspected and doc.get("photo_set_interpretation") == "no_inspectable_photos":
        errors.append("photo_set_interpretation says no_inspectable_photos but a photo was inspected")

    upload_refs = [u["ref"] for u in doc.get("photo_upload_order", [])]
    if len(upload_refs) != len(set(upload_refs)):
        errors.append("photo_upload_order lists a photo more than once")
    for ref in upload_refs:
        if ref not in inspected:
            errors.append(f"photo_upload_order: {ref} is not an inspected photo")
    for u in doc.get("photo_upload_order", []):
        for pattern, why in LISTING_FORBIDDEN:
            if u["note"] and pattern.search(u["note"]) and why != "serial identifier":
                errors.append(f"photo_upload_order note for {u['ref']} contains a {why}")

    errors.extend(price_errors(doc, by_id))

    en = doc.get("listing_translations", {}).get("en", {})
    nullness = {doc.get("listing_title") is None, doc.get("listing_description") is None,
                en.get("title") is None, en.get("description") is None}
    if len(nullness) != 1:
        errors.append("German and English title/description must be all present or all null")
    for text in _listing_texts(doc):
        for pattern, why in LISTING_FORBIDDEN:
            if pattern.search(text):
                errors.append(f"listing copy contains a {why}: {pattern.search(text).group(0)!r}")

    for q in doc.get("clarification_questions", []):
        for path in q["field_paths"]:
            if not minischema.pointer_exists(doc, path):
                errors.append(f"question {q['id']}: field_path {path} does not resolve")
    qids = [q["id"] for q in doc.get("clarification_questions", [])]
    if len(qids) != len(set(qids)):
        errors.append("clarification question ids are not unique")
    for u in doc.get("unknowns", []):
        if not minischema.pointer_exists(doc, u["field_path"]):
            errors.append(f"unknown field_path {u['field_path']} does not resolve")
    return errors


def price_errors(doc, by_id):
    """Every price needs a stated, matching basis. See references/pricing.md."""
    price = doc.get("price_estimate")
    if price is None:
        return []
    errors = []
    if doc.get("item_type") is None:
        errors.append("price_estimate must be null while item_type is unknown")
    if not price["low"] <= price["suggested"] <= price["high"]:
        errors.append("price_estimate needs low <= suggested <= high")
    refs = [by_id[r] for r in price["evidence_refs"] if r in by_id]
    for r in price["evidence_refs"]:
        if r not in by_id:
            errors.append(f"price_estimate: evidence_ref {r} does not exist")
    basis = price["basis"]
    if basis == "reference_new_price" and not any(
            e["source"] == "external_reference" and e["url"] for e in refs):
        errors.append("reference_new_price needs external_reference evidence with a URL")
    if basis == "user_comparables" and not any(e["source"] == "user_statement" for e in refs):
        errors.append("user_comparables needs user_statement evidence with the pasted prices")
    if basis == "model_knowledge":
        # Cited pages may still appear as context (e.g. "no current new price found").
        if not any(e["source"] == "inference" and e["certainty"] == "tentative" for e in refs):
            errors.append("model_knowledge price needs tentative inference evidence")
    if price["scope"] != "lot" and price["lot_total_suggested"] is not None and (doc.get("quantity") or 0) < 2:
        errors.append("lot_total_suggested needs a quantity of at least 2")
    return errors


def run_case_check(check, doc, previous):
    op = check["op"]
    value = check.get("value")
    if "pointer" in check:
        actual = minischema.resolve_pointer(doc, check["pointer"])
        if actual is minischema._MISSING:
            return f"{check['pointer']} does not exist"
        if op == "equals" and actual != value:
            return f"{check['pointer']} is {actual!r}, expected {value!r}"
        if op == "not_equals" and actual == value:
            return f"{check['pointer']} must not be {value!r}"
        if op == "is_null" and actual is not None:
            return f"{check['pointer']} is {actual!r}, expected null"
        if op == "contains" and value not in actual:
            return f"{check['pointer']} does not contain {value!r}"
        if op == "max_length" and len(actual) > value:
            return f"{check['pointer']} has {len(actual)} items, max {value}"
        if op not in ("equals", "not_equals", "is_null", "contains", "max_length"):
            return f"unknown op {op}"
        return None
    texts = " \n".join(_listing_texts(doc)).lower()
    if op == "listing_not_contains":
        hits = [v for v in value if v.lower() in texts]
        return f"listing copy contains {hits}" if hits else None
    if op == "listing_contains":
        misses = [v for v in value if v.lower() not in texts]
        return f"listing copy lacks {misses}" if misses else None
    if op == "no_visual_evidence":
        bad = [e["id"] for e in doc["evidence"] if e["source"] in ("photo", "readable_label")]
        return f"visual evidence without inspected photos: {bad}" if bad else None
    if op == "all_photos_uninspected":
        bad = [p["ref"] for p in doc["photos"] if p["inspected"] or p["shows"] is not None]
        return f"photos marked as inspected: {bad}" if bad else None
    if op == "preserved_from_previous_turn":
        if previous is None:
            return "no previous turn to compare with"
        changed = [p for p in value
                   if minischema.resolve_pointer(doc, p) != minischema.resolve_pointer(previous, p)]
        return f"changed although confirmed earlier: {changed}" if changed else None
    if op == "evidence_ids_preserved":
        if previous is None:
            return "no previous turn to compare with"
        # Confirmation and certainty may legitimately change; what was recorded may not.
        identity = ("field_path", "source", "photo_ref", "observation", "url")
        current = {e["id"]: tuple(e[k] for k in identity) for e in doc["evidence"]}
        lost = [e["id"] for e in previous["evidence"] if current.get(e["id"]) != tuple(e[k] for k in identity)]
        return f"earlier evidence records changed or removed: {lost}" if lost else None
    return f"unknown op {op}"


def check_examples(schema):
    problems = []
    data = json.loads((SKILL_DIR / "examples" / "cases.json").read_text(encoding="utf-8"))
    if data.get("schema_version") != schema["properties"]["schema_version"]["const"]:
        problems.append("cases.json schema_version does not match schema.json")
    try:
        import jsonschema
        validator = jsonschema.Draft202012Validator(schema)
    except ImportError:
        validator = None
    seen = set()
    for case in data["cases"]:
        if case["id"] in seen:
            problems.append(f"duplicate case id {case['id']}")
        seen.add(case["id"])
        previous = None
        for t, turn in enumerate(case["turns"], start=1):
            where = f"{case['id']} turn {t}"
            doc = turn["expected_output"]
            if turn.get("response_format") not in ("default", "json_only"):
                problems.append(f"{where}: response_format must be default or json_only")
            problems.extend(f"{where}: schema {e}" for e in minischema.validate(doc, schema))
            if validator is not None:
                problems.extend(f"{where}: jsonschema {e.message}" for e in validator.iter_errors(doc))
            problems.extend(f"{where}: {e}" for e in semantic_errors(doc))
            refs = [p["ref"] for p in doc["photos"]]
            supplied = [p["ref"] for c_turn in case["turns"][:t] for p in c_turn["input"]["photos"]]
            if refs != supplied:
                problems.append(f"{where}: output photos {refs} do not match supplied photos {supplied}")
            if doc["revision"] != t:
                problems.append(f"{where}: revision should be {t}")
            for check in turn.get("checks", []):
                failure = run_case_check(check, doc, previous)
                if failure:
                    problems.append(f"{where}: check failed: {failure}")
            previous = doc
    return problems


# --------------------------------------------------------------------------- packaging, version, hygiene

def read_version():
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def check_version(version):
    problems = []
    if not SEMVER_RE.match(version):
        problems.append(f"VERSION {version!r} is not MAJOR.MINOR.PATCH")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{version}]" not in changelog:
        problems.append(f"CHANGELOG.md has no '## [{version}]' entry")
    return problems


def check_packaging():
    problems = []
    def load(rel):
        try:
            return json.loads((ROOT / rel).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{rel}: {exc}")
            return {}

    cc_plugin = load("packaging/claude-code/plugin.json")
    cc_market = load("packaging/claude-code/marketplace.json")
    cx_plugin = load("packaging/codex/plugin.json")
    cx_market = load("packaging/codex/marketplace.json")
    for rel, manifest in (("claude-code/plugin.json", cc_plugin), ("codex/plugin.json", cx_plugin)):
        if manifest.get("name") != PLUGIN_NAME:
            problems.append(f"{rel}: name must be {PLUGIN_NAME!r}")
        if "version" in manifest:
            problems.append(f"{rel}: omit 'version'; the build injects it from VERSION")
    if cx_plugin.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
        problems.append("codex/plugin.json must declare the Agent Plugins 1.0.0 $schema")
    allowed_cx = {"$schema", "name", "version", "description", "author", "homepage", "repository",
                  "license", "keywords", "extensions"}
    if set(cx_plugin) - allowed_cx:
        problems.append(f"codex/plugin.json has fields outside the Agent Plugins schema: {sorted(set(cx_plugin) - allowed_cx)}")
    for rel, market in (("claude-code/marketplace.json", cc_market), ("codex/marketplace.json", cx_market)):
        entries = market.get("plugins", [])
        if len(entries) != 1 or entries[0].get("name") != PLUGIN_NAME:
            problems.append(f"{rel}: must list exactly the {PLUGIN_NAME!r} plugin")
    if cc_market and not cc_market.get("owner", {}).get("name"):
        problems.append("claude-code/marketplace.json: owner.name is required")
    for rel in ("packaging/claude-code/INSTALL.md", "packaging/codex/INSTALL.md"):
        if not (ROOT / rel).is_file():
            problems.append(f"{rel}: missing")
    return problems


def iter_repo_files():
    # In a git checkout, scan what could be committed (tracked + untracked, minus .gitignore'd).
    if (ROOT / ".git").exists() and shutil.which("git"):
        proc = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"],
                              cwd=ROOT, capture_output=True, text=True)
        if proc.returncode == 0:
            for name in sorted(filter(None, proc.stdout.split("\0"))):
                path = ROOT / name
                if path.is_file():
                    yield path, Path(name)
            return
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(part in SCAN_SKIP_DIRS for part in rel.parts):
            continue
        if path.is_file():
            yield path, rel


def check_hygiene():
    problems = []
    for path, rel in iter_repo_files():
        if path.suffix.lower() in PRIVATE_SUFFIXES or path.name in PRIVATE_NAMES:
            problems.append(f"{rel}: private or binary file type must not be committed")
            continue
        if path.name == ".DS_Store":
            problems.append(f"{rel}: OS metadata file")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(f"{rel}: unexpected binary file")
            continue
        if rel.as_posix() == "scripts/validate.py" or rel.parts[0] == "tests":
            continue  # these files contain the detection patterns and synthetic negatives
        for pattern, why in SECRET_PATTERNS:
            if pattern.search(text):
                problems.append(f"{rel}: possible {why}")
    return problems


def run_external():
    """Optional official validators, run only when installed."""
    results = []
    if shutil.which("skills-ref"):
        proc = subprocess.run(["skills-ref", "validate", str(SKILL_DIR)], capture_output=True, text=True)
        results.append(("skills-ref validate", proc.returncode, (proc.stdout + proc.stderr).strip()))
    else:
        results.append(("skills-ref validate", None, "not installed; skipped"))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dist", type=Path, help="also verify release archives in this directory")
    parser.add_argument("--external", action="store_true", help="also run skills-ref if it is installed")
    parser.add_argument("--output", type=Path, help="validate one metadata JSON document (e.g. a real model answer) and exit")
    args = parser.parse_args(argv)

    if args.output:
        doc = json.loads(args.output.read_text(encoding="utf-8"))
        problems = [f"schema {e}" for e in minischema.validate(doc, load_schema())]
        problems += semantic_errors(doc) if not problems else []
        for p in problems:
            print(f"FAIL  {p}")
        print("OK" if not problems else f"{len(problems)} problem(s)")
        return 0 if not problems else 1

    report = Report()
    version = read_version()
    report.check("version consistency", check_version(version))
    report.check("SKILL.md format and resources", check_skill_dir(SKILL_DIR, version))
    schema = load_schema()
    report.check("schema.json validity", check_schema_file(schema))
    report.check("examples against schema and rules", check_examples(schema))
    report.check("packaging configuration", check_packaging())
    report.check("secrets and private files", check_hygiene())
    if args.dist:
        import build_releases
        report.check(f"release archives in {args.dist}", build_releases.verify_dist(args.dist.resolve(), version))
    if args.external:
        for label, code, output in run_external():
            if code is None:
                print(f"SKIP  {label}: {output}")
            else:
                report.check(label, [] if code == 0 else [output])

    for label in report.passed:
        print(f"PASS  {label}")
    for error in report.errors:
        print(f"FAIL  {error}")
    try:
        import jsonschema  # noqa: F401
        print("info  jsonschema cross-check: enabled")
    except ImportError:
        print("info  jsonschema cross-check: not installed (built-in validator only)")
    print("OK" if report.ok() else f"{len(report.errors)} problem(s)")
    return 0 if report.ok() else 1


if __name__ == "__main__":
    sys.exit(main())
