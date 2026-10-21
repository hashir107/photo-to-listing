# photo-to-listing: the ReLoop skill

**ReLoop** is an [Agent Skill](https://agentskills.io/specification) for second-hand items. It turns photos of an item or bundle, plus an optional one-line note, into four things:

- a compact item summary,
- a German listing title and description in Kleinanzeigen style, followed by an English version,
- up to three targeted clarification questions, and
- structured JSON metadata that validates against a versioned schema.

You can answer the questions over later turns. The result is updated in place, and confirmed facts and corrections are kept.

> Version 0.2.0. The skill ID is `reloop`, because the spec requires lowercase names. Its display name is "ReLoop".

## What it does and does not do

| In scope | Out of scope |
| --- | --- |
| Identifying an item from photos, labels and packaging | Prices, price estimates and market research |
| Separating what was seen, what the user said, external sources and inferences | Inventory, saved collections or a database |
| Condition kept separate from function, plus defects and accessories | Keep/sell/give-away decisions and selling status |
| German and English listing copy for you to paste into Kleinanzeigen | Logging in to or publishing on any marketplace |
| Multi-turn clarification | Buyer messaging, payments, shipping, cloud sync |

Kleinanzeigen is the target writing style, not an integration. There is no backend, MCP server or external API. Basic use needs no API keys.

## Requirements

- An assistant that can view the images you attach: Claude (claude.ai or the desktop app), Claude Code or Codex, used with a vision-capable model.
- If the host cannot view images, ReLoop says so and asks you to re-attach them. It never pretends to have inspected a photo.
- Web browsing is optional. It is used only when you ask, or when a material identification question needs checking.

## Repository layout

```
skills/reloop/              The one authoritative skill (shipped in every package)
  SKILL.md                  Activation description and workflow
  schema.json               JSON Schema 2020-12, schema_version 0.2.0
  references/               Extraction rules; listing-copy rules
  examples/cases.json       9 worked examples / behavioural fixtures
packaging/claude-code/      Claude Code plugin + marketplace manifests, install notes
packaging/codex/            Codex (Agent Plugins) manifest + marketplace, install notes
scripts/validate.py         All source checks (stdlib only)
scripts/build_releases.py   Reproducible release build + archive verification
scripts/minischema.py       Stdlib JSON Schema subset validator
tests/                      Unit tests; tests/image-eval/ synthetic SVG test images
docs/compatibility.md       Official sources, verification date, install results
docs/evaluation.md          What has and has not been tested, and how
```

## Install

Build the packages (see [Build and validate](#build-and-validate)) or download them from a CI run. Each package is built from `skills/reloop/`.

### Claude (claude.ai or desktop app): `photo-to-listing-skill-v0.2.0.zip`

1. Go to **Customize > Skills** and upload `photo-to-listing-skill-v0.2.0.zip`. The ZIP's top-level folder is `reloop/`, as Anthropic's packaging guide requires.
2. Turn the skill on. Custom skills on claude.ai need a plan with Skills support and code execution enabled; see [compatibility](docs/compatibility.md).

### Claude Code: `photo-to-listing-claude-code-v0.2.0.zip`

```bash
unzip photo-to-listing-claude-code-v0.2.0.zip
claude plugin marketplace add ./photo-to-listing-claude-code-v0.2.0
claude plugin install photo-to-listing@photo-to-listing-local
```

To try it without installing: `claude --plugin-dir ./photo-to-listing-claude-code-v0.2.0/plugins/photo-to-listing`. To invoke it explicitly, use `/photo-to-listing:reloop`. The package's `INSTALL.md` has details.

### Codex: `photo-to-listing-codex-v0.2.0.zip`

```bash
unzip photo-to-listing-codex-v0.2.0.zip
codex plugin marketplace add ./photo-to-listing-codex-v0.2.0
```

Then install **ReLoop** from the **photo-to-listing (local)** marketplace in the Plugins Directory of Codex in the ChatGPT desktop app. If you want the skill only, without the plugin:

```bash
cp -R photo-to-listing-codex-v0.2.0/plugins/photo-to-listing/skills/reloop ~/.agents/skills/reloop
```

Invoke it with `$reloop` or pick it from `/skills`. The package's `INSTALL.md` has details.

## Use

1. Attach one or more photos of the same item or bundle. Include a close-up of any label, type plate or packaging side.
   - Claude: attach the images in the chat.
   - Claude Code: paste or drag the images in, or give their file paths.
   - Codex CLI: `codex -i a.jpg,b.jpg "…"`, or paste the images into the composer.
2. Add an optional one-line note, for example *"24 LG monitors, office closing."*
3. Ask for a listing, for example *"Draft a Kleinanzeigen listing."* Ask for *"JSON only"* if you want just the metadata.
4. Answer any of the questions in later turns, in a few words. Partial answers are fine, and you can stop answering at any point.

### Example (abridged)

Input: photos of several monitors, plus a close-up of one rear label, plus the note "24 LG monitors, office closing."

**A. Item summary**

| | |
| --- | --- |
| Item | LG computer monitors |
| Quantity | 24 (from your note; about 8 visible) |
| Model | Unconfirmed: one unit's label reads 24MK430H |
| Condition | Not assessed for the whole batch; a scratch on one bezel |
| Function | Unknown (screens off) |

**B. Kleinanzeigen-Formular**: the rows follow the "Anzeige aufgeben" form from top to bottom.

| Feld | Eintrag |
| --- | --- |
| Gebot / Gesuch | Ich biete |
| Bilder | 1. photo_1 (Titelbild) · 2. photo_3 · 3. photo_2: Seriennummer abdecken |
| Titel (40/65) | 24 × LG Computermonitore (Büroauflösung) |
| Kategorie | Elektronik > Monitore (Vorschlag; Kleinanzeigen wählt nach dem Titel automatisch vor) |
| Eigenschaften und Versand | Zustand: gebraucht, Gebrauchsspuren (im Formular auswählen) · Versand: selbst festlegen |
| Beschreibung (n/4000) | siehe unten |
| Preis / Preistyp | selbst festlegen |
| Ort / Name | selbst ausfüllen |

```text
24 × LG Computermonitore (Büroauflösung)
```

```text
Angeboten werden 24 Computermonitore von LG aus einer Büroauflösung.

Zustand: Gebraucht. Auf den Fotos sind Gebrauchsspuren zu sehen, z. B. ein kurzer Kratzer am unteren Rahmen eines Monitors.
…
```

English version: **24 × LG computer monitors (office clearance)**, with the matching description.

**C. Clarifications**

1. The rear label on one monitor reads 24MK430H. Are all 24 monitors this model?
2. Have the monitors been tested? Do all of them power on?
3. Do you want to sell all 24 as one lot, or individually?

**D. Structured metadata**: JSON with `evidence` records such as `{"field_path": "/units/0/model", "source": "readable_label", "photo_ref": "photo_2", "certainty": "supported"}`.

Follow-up example: you reply "All the same model, all tested and working, sold as one lot." ReLoop then sets `model`, `functional_status: "working"` (user-reported) and `sale_configuration: "bundle"`, notes what changed, and returns the revised listing.

Full worked examples are in [`skills/reloop/examples/cases.json`](skills/reloop/examples/cases.json).

## Build and validate

Requires Python 3.9 or later and nothing else.

```bash
python3 scripts/validate.py                    # SKILL.md, schema, examples, packaging, version, secrets
python3 -m unittest discover -s tests          # 52 unit tests including negative cases
python3 scripts/build_releases.py              # validate, build dist/*.zip + SHA256SUMS.txt, verify archives
python3 scripts/validate.py --dist dist        # re-verify existing archives
python3 scripts/validate.py --output out.json  # check one real model answer against schema and rules
```

Optional cross-checks, also run in CI:

```bash
pip install jsonschema "skills-ref @ git+https://github.com/agentskills/agentskills.git#subdirectory=skills-ref"
python3 scripts/validate.py --external
claude plugin validate dist-unzipped/photo-to-listing-claude-code-v0.2.0   # if Claude Code is installed
```

The build is reproducible: identical sources give byte-identical ZIPs. The workflow in `.github/workflows/validate.yml` validates, tests, builds and uploads the packages as workflow artifacts. It never publishes a release.

## Known limitations

- The quality of image recognition depends on the host model. The fixtures in this repo are text-based and do not prove recognition accuracy; see [docs/evaluation.md](docs/evaluation.md).
- Different hosts and models may follow the skill differently. Behaviour is not guaranteed to be identical across Claude, Claude Code and Codex.
- Codex plugin installation was not tested in this environment; see [docs/compatibility.md](docs/compatibility.md).
- Category suggestions are human-readable paths, not official Kleinanzeigen category IDs.
- No license has been chosen yet, so all rights are reserved by default until the owner adds one.
