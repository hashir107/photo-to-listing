<p align="center"><img src="skills/reloopit/assets/logo.png" width="160" alt="ReLoopIt logo"></p>

<h1 align="center">ReLoopIt</h1>

<p align="center"><strong>Snap it, List it, ReLoopIt.</strong></p>

**ReLoopIt** is an [Agent Skill](https://agentskills.io/specification) for second-hand items. It turns photos of an item or bundle, plus an optional one-line note, into four things:

- a compact item summary,
- a Kleinanzeigen form table: German title and description, category and condition hints, followed by the English version, plus an optional price suggestion if you want one,
- up to three targeted clarification questions, and
- structured JSON metadata that validates against a versioned schema.

You can answer the questions over later turns. The result is updated in place, and confirmed facts and corrections are kept.

> Version 0.5.0. Formerly called **ReLoop** (up to v0.4.3). The skill ID, plugin and download packages are named `reloopit`, because the Agent Skills spec requires lowercase names; the display name is "ReLoopIt".

## Try it

1. **Download** the ZIP for your app from the [latest release](https://github.com/hashir107/reloopit/releases/latest):
   - **Claude** (claude.ai, desktop or mobile app): `reloopit-skill-v0.5.0.zip`. Turn on code execution under **Settings → Capabilities**. Then go to **Customize → Skills**, click **+**, choose **Upload a skill** and pick the ZIP without unzipping it. [Details](#claude-and-claude-code)
   - **ChatGPT desktop app or Codex:** copy the `reloopit` folder into `~/.agents/skills/` ([details](#codex-and-the-chatgpt-desktop-app)), or let your coding agent do it ([agent install](#quick-install-with-a-coding-agent-codex-chatgpt-desktop-app-claude-code)).
   - **Claude Code:** copy the `reloopit` folder into `~/.claude/skills/`, or use the agent install. [Details](#claude-and-claude-code)
2. **Use it.** Start a new chat, attach a few photos of the item (include a close-up of any label), add one line such as *"24 LG monitors, office closing"*, and ask for a Kleinanzeigen listing. Answer the follow-up questions if you like. To get a price suggestion, paste a few comparable prices or allow a web search when ReLoopIt offers it.
3. **Tell me how it went:** see [Feedback](#feedback). No GitHub account is needed to download; you need one to open an issue.

## What it does and does not do

| In scope | Out of scope |
| --- | --- |
| Identifying an item from photos, labels and packaging | Scraping marketplaces or automated market research |
| Separating what was seen, what the user said, external sources and inferences | Inventory, saved collections or a database |
| Condition kept separate from function, plus defects and accessories | Keep/sell/give-away decisions and selling status |
| German and English listing copy for you to paste into Kleinanzeigen | Logging in to or publishing on any marketplace |
| Optional price suggestions on request, with a stated basis (your comparables, a cited new price or a labelled fallback) | Buyer messaging, payments, shipping, cloud sync |
| Multi-turn clarification | |

Kleinanzeigen is the target writing style, not an integration. There is no backend, MCP server or external API. Basic use needs no API keys.

## Requirements

- An assistant that can view the images you attach: Claude (claude.ai or the desktop app), Claude Code or Codex, used with a vision-capable model.
- If the host cannot view images, ReLoopIt says so and asks you to re-attach them. It never pretends to have inspected a photo.
- Web browsing is optional. It is used when you ask, when a material identification question needs checking, or, if you allow it, to look up a current new price for a price suggestion.

## Repository layout

```
skills/reloopit/              The one authoritative skill (shipped in every package)
  SKILL.md                  Activation description and workflow
  LICENSE.txt               MIT license (identical copy of LICENSE)
  agents/openai.yaml        Display name and icon for ChatGPT desktop / Codex
  assets/                   ReLoopIt logo (logo.png, icon-small.png)
  schema.json               JSON Schema 2020-12, schema_version 0.4.0
  references/               Extraction rules; listing-copy rules; pricing (opt-in)
  examples/cases.json       11 worked examples / behavioural fixtures
packaging/claude-code/      Claude Code plugin + marketplace manifests, install notes
packaging/codex/            Codex (Agent Plugins) manifest + marketplace, install notes
scripts/validate.py         All source checks (stdlib only)
scripts/build_releases.py   Reproducible release build + archive verification
scripts/minischema.py       Stdlib JSON Schema subset validator
tests/                      Unit tests; tests/image-eval/ synthetic SVG test images
docs/compatibility.md       Official sources, verification date, install results
docs/evaluation.md          What has and has not been tested, and how
LICENSE                     MIT license
```

## Install

### Upgrading from ReLoop (v0.4.3 or earlier)

ReLoop was renamed to **ReLoopIt** in v0.5.0. The new skill is called `reloopit`, so remove the old one first. Otherwise both versions stay installed:

- **Claude:** go to **Customize → Skills**, delete **reloop**, then upload `reloopit-skill-v0.5.0.zip`.
- **ChatGPT desktop / Codex:** `rm -rf ~/.agents/skills/reloop`, then install `reloopit` as described below.
- **Claude Code:** `rm -rf ~/.claude/skills/reloop`. If you installed the plugin, run `claude plugin uninstall photo-to-listing@photo-to-listing-local` and `claude plugin marketplace remove photo-to-listing-local`.

### Quick install with a coding agent (Codex, ChatGPT desktop app, Claude Code)

If you use an agent such as Codex, you can paste it this prompt:

> Install the ReLoopIt skill from https://github.com/hashir107/reloopit by following the README section "Quick install with a coding agent".

#### Instructions for the agent

The skill is the **whole folder** `skills/reloopit/` in this repository:

```
skills/reloopit/
├── SKILL.md                     # instructions (frontmatter name: reloopit)
├── LICENSE.txt                  # MIT license
├── agents/openai.yaml           # display name + icon for ChatGPT desktop / Codex
├── assets/                      # logo.png, icon-small.png
├── schema.json                  # JSON Schema for the metadata output
├── references/                  # extraction-rules.md, kleinanzeigen-copy.md, pricing.md
└── examples/cases.json          # worked examples
```

Copy all of it. `SKILL.md` on its own is not enough, because it reads the files next to it. Install it as a folder named exactly `reloopit` in the skills directory for the user's tool:

| Tool | Skills directory |
| --- | --- |
| Codex CLI, Codex IDE extension, ChatGPT desktop app | `~/.agents/skills` (or `<repo>/.agents/skills` for one repository only) |
| Claude Code | `~/.claude/skills` (or `<repo>/.claude/skills` for one repository only) |

**Prerequisite:** `git`. The repository is public, so no GitHub login is needed. The script falls back to the GitHub CLI or SSH only if a plain HTTPS clone fails, for example behind a proxy.

Run this script. Set `DEST` to the skills directory from the table; it defaults to `~/.agents/skills`. It is safe to re-run, and re-running updates to the latest version. It only touches `$DEST/reloopit` and a temporary folder.

```bash
set -euo pipefail
DEST="${DEST:-$HOME/.agents/skills}"
REPO="hashir107/reloopit"
TMP="$(mktemp -d)"
# Public repository: plain HTTPS first, then the GitHub CLI, then SSH (no interactive prompts).
if GIT_TERMINAL_PROMPT=0 git clone --depth 1 --quiet "https://github.com/$REPO.git" "$TMP/src" 2>/dev/null; then :
elif command -v gh >/dev/null 2>&1 && gh repo clone "$REPO" "$TMP/src" -- --depth 1 --quiet 2>/dev/null; then :
elif GIT_SSH_COMMAND="ssh -o BatchMode=yes" git clone --depth 1 --quiet "git@github.com:$REPO.git" "$TMP/src" 2>/dev/null; then :
else
  rm -rf "$TMP"
  echo "Could not download $REPO: check your internet connection, then retry." >&2
  exit 1
fi
mkdir -p "$DEST"
rm -rf "$DEST/reloopit"
cp -R "$TMP/src/skills/reloopit" "$DEST/reloopit"
rm -rf "$TMP"
# Verify
grep -qx 'name: reloopit' "$DEST/reloopit/SKILL.md"
for f in LICENSE.txt schema.json references/extraction-rules.md references/kleinanzeigen-copy.md references/pricing.md examples/cases.json; do
  test -f "$DEST/reloopit/$f" || { echo "missing $f"; exit 1; }
done
echo "ReLoopIt installed at $DEST/reloopit"
```

Then tell the user to **restart** the app or CLI. The skill is invoked with `$reloopit` or `/skills` in Codex, `@reloopit` in the ChatGPT desktop app, and `/reloopit` in Claude Code, or it activates when they ask for a Kleinanzeigen listing from photos. Do not edit the skill files, install plugins, or change any other configuration as part of this install.

### Get the packages

Each package is built from `skills/reloopit/`. You can get them in any of three ways:

- **Releases (easiest):** download the ZIPs from the [latest release](https://github.com/hashir107/reloopit/releases/latest). No login is needed. `SHA256SUMS.txt` on the same page lets you check the downloads.
- **Build them locally** with `python3 scripts/build_releases.py`. The ZIPs appear in `dist/`.
- **From a CI run:** open the repository's **Actions** tab, open the latest **validate** run, and download the **reloopit-packages** artifact. That artifact is itself a ZIP: unzip it once to get the three package ZIPs, and never upload the outer artifact ZIP.

| You use | Package |
| --- | --- |
| Claude apps (claude.ai, desktop, mobile) and Claude Code | `reloopit-skill-v0.5.0.zip`. Claude Code can also use the `skills/reloopit` folder or `reloopit-claude-code-v0.5.0.zip` |
| Codex or the ChatGPT desktop app | `reloopit-codex-v0.5.0.zip`, or the `skills/reloopit` folder from this repository |

### Claude and Claude Code

**Option A: upload once to your Claude account (claude.ai, desktop and mobile app).** Upload the skill from claude.ai or the Claude desktop app. The upload needs a ZIP file, so do it on a computer.

1. **Turn on code execution**, which skills need.
   - Free, Pro or Max: **Settings → Capabilities**, then turn on **Code execution and file creation**.
   - Team or Enterprise: an admin enables it under **Organization settings → Plugins & skills**.
2. **Upload the skill.** Go to **Customize → Skills**, click **+**, then **+ Create skill → Upload a skill**. Choose `reloopit-skill-v0.5.0.zip`. Upload the ZIP as it is; don't unzip it. Its top-level folder is `reloopit/`, which is what Claude expects.
3. **Switch it on.** Make sure **reloopit** is enabled in the skills list.
4. **Use it.** Start a new chat, attach your photos, add a short note and ask for a listing, for example *"24 LG monitors, office closing. Draft a Kleinanzeigen listing."* If it doesn't kick in, add *"Use the ReLoopIt skill."*

**Updating to a new version:** delete the old **reloopit** skill under **Customize → Skills**, then upload the new ZIP.

Skills you upload are tied to your Claude account. Anthropic's help article doesn't say whether uploaded skills appear in the iOS and Android apps, so this hasn't been confirmed. If ReLoopIt doesn't show up on your phone, open claude.ai in the phone's browser instead.

According to Anthropic's help article, Claude Code also loads skills from your Claude account when it is signed in with that account. This is a one-way sync, and it doesn't happen with an API key or a cloud provider. After Option A, ReLoopIt may therefore already be available in Claude Code; type `/reloopit` to check. This sync hasn't been tested for ReLoopIt.

**Option B: Claude Code only, as a skill folder.** Use this if the sync doesn't apply, or if you only use Claude Code. It is the same folder as for Codex, placed in Claude Code's skills directory:

```bash
mkdir -p ~/.claude/skills
cp -R skills/reloopit ~/.claude/skills/reloopit
```

Run this from a clone of this repository, or use the agent script above with `DEST=~/.claude/skills`. To make it available in one project only, copy the folder to `<project>/.claude/skills/reloopit` instead. Start a new Claude Code session, then type `/reloopit`, or ask for a Kleinanzeigen listing and give it your photos: paste or drag them in, or give their file paths.

**Option C: Claude Code as a plugin.** Unzip `reloopit-claude-code-v0.5.0.zip`, then:

```bash
claude plugin marketplace add ./reloopit-claude-code-v0.5.0
claude plugin install reloopit@reloopit-local
```

With the plugin, the skill is invoked as `/reloopit:reloopit`. To try it without installing: `claude --plugin-dir ./reloopit-claude-code-v0.5.0/plugins/reloopit`. The package's `INSTALL.md` has details.

Use only one of these in Claude Code (account sync, the skill folder, or the plugin). Otherwise ReLoopIt may be listed more than once.

### Codex and the ChatGPT desktop app

**Option A: install the skill folder (recommended).** This works in Codex CLI, the Codex IDE extension and the ChatGPT desktop app, which all read skills from `~/.agents/skills`.

1. Copy the skill into your personal skills folder. From a clone of this repository:

   ```bash
   mkdir -p ~/.agents/skills
   cp -R skills/reloopit ~/.agents/skills/reloopit
   ```

   Or from the unzipped Codex package:

   ```bash
   cp -R reloopit-codex-v0.5.0/plugins/reloopit/skills/reloopit ~/.agents/skills/reloopit
   ```

   To make it available in one repository only, copy it to `<repo>/.agents/skills/reloopit` instead.
2. **Restart** Codex or the ChatGPT desktop app.
3. **Use it.**
   - **Codex CLI:** attach the photos with `codex -i photo1.jpg,photo2.jpg "24 LG monitors, office closing. Draft a Kleinanzeigen listing."`, or paste images into the composer. Invoke the skill with `$reloopit` or pick it from `/skills`.
   - **ChatGPT desktop app:** open **Skills** in the sidebar to check that **reloopit** is listed. In a chat, type **@** and choose **reloopit**, then drag in your photos while holding **Shift** and add your note.

**Updating:** replace the folder (`rm -rf ~/.agents/skills/reloopit`, then copy the new one) and restart.

Standalone skills are not available on chatgpt.com or in the ChatGPT phone app. Only skills bundled in plugins from the Plugins Directory reach those.

**Option B: install as a plugin.** Unzip `reloopit-codex-v0.5.0.zip`, then register its local marketplace (this needs the Codex CLI):

```bash
codex plugin marketplace add ./reloopit-codex-v0.5.0
```

Then install **ReLoopIt** from **Plugins → ReLoopIt (local)** in the ChatGPT desktop app. The package's `INSTALL.md` has details. This route hasn't been tested yet; see [compatibility](docs/compatibility.md).

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

**Hinweis zu Fotos:** photo_2 – Seriennummer abdecken.

**B. Kleinanzeigen-Formular**: one table in the order of the "Anzeige aufgeben" form.

| Feld | Eintrag |
| --- | --- |
| Titel (40/65) | 24 × LG Computermonitore (Büroauflösung) |
| Kategorie | Elektronik > Monitore (Vorschlag; Kleinanzeigen wählt nach dem Titel automatisch vor) |
| Eigenschaften und Versand | Zustand: gebraucht, Gebrauchsspuren (im Formular auswählen) · Versand: selbst festlegen |
| Beschreibung (293/4000) | Angeboten werden 24 Computermonitore von LG aus einer Büroauflösung.<br><br>Zustand: Gebraucht. Auf den Fotos sind Gebrauchsspuren zu sehen, z. B. ein kurzer Kratzer am unteren Rahmen eines Monitors.<br>… |
| Preis | noch kein Vorschlag (siehe Frage unten) |
| Title (EN) | 24 × LG computer monitors (office clearance) |
| Description (EN) | 24 LG computer monitors from an office clearance.<br><br>Condition: Used. … |

### Price suggestions (optional)

ReLoopIt does not estimate a price unless you want one. The first answer ends with a one-line offer:

> **Preisvorschlag?** Vergleichsanzeigen mit Preisen einfügen, die Websuche erlauben, oder den Preis selbst festlegen?

To get a price, paste comparable prices or say the web search is OK. Reply "mache ich selbst" and it will not ask again. When you opt in, ReLoopIt states the basis of the price and uses the best basis available, in this order (see [`references/pricing.md`](skills/reloopit/references/pricing.md)):

1. **Your comparables.** Paste 2–5 prices of similar Kleinanzeigen listings, for example "Ähnliche Anzeigen: 45 €, 50 €, 60 €". ReLoopIt takes the median and adjusts it for condition, function and quantity. This is the most accurate basis for Kleinanzeigen.
2. **A cited new price.** With web search, ReLoopIt looks up the current new price from a manufacturer, retailer or price-comparison page, cites the URL, and applies documented depreciation bands.
3. **A model-knowledge fallback.** With no sources, it gives a cautious range labelled "ungeprüft (Modellwissen)".

ReLoopIt never fetches or scrapes Kleinanzeigen or eBay pages, and never puts the price in the title or description. Your answers about age, function and completeness tighten the range.

**C. Clarifications**

1. The rear label on one monitor reads 24MK430H. Are all 24 monitors this model?
2. Have the monitors been tested? Do all of them power on?
3. Do you want to sell all 24 as one lot, or individually?

**Preisvorschlag?** Vergleichsanzeigen mit Preisen einfügen, die Websuche erlauben, oder den Preis selbst festlegen?

**D. Structured metadata**: JSON with `evidence` records such as `{"field_path": "/units/0/model", "source": "readable_label", "photo_ref": "photo_2", "certainty": "supported"}`.

Follow-up example: you reply "All the same model, all tested and working, sold as one lot." ReLoopIt then sets `model`, `functional_status: "working"` (user-reported) and `sale_configuration: "bundle"`, notes what changed, and returns the revised listing.

Full worked examples are in [`skills/reloopit/examples/cases.json`](skills/reloopit/examples/cases.json).

## Build and validate

Requires Python 3.9 or later and nothing else.

```bash
python3 scripts/validate.py                    # SKILL.md, schema, examples, packaging, version, secrets
python3 -m unittest discover -s tests          # 66 unit tests including negative cases
python3 scripts/build_releases.py              # validate, build dist/*.zip + SHA256SUMS.txt, verify archives
python3 scripts/validate.py --dist dist        # re-verify existing archives
python3 scripts/validate.py --output out.json  # check one real model answer against schema and rules
```

Optional cross-checks, also run in CI:

```bash
pip install jsonschema "skills-ref @ git+https://github.com/agentskills/agentskills.git#subdirectory=skills-ref"
python3 scripts/validate.py --external
claude plugin validate dist-unzipped/reloopit-claude-code-v0.5.0   # if Claude Code is installed
```

The build is reproducible: identical sources give byte-identical ZIPs. The workflow in `.github/workflows/validate.yml` validates, tests, builds and uploads the packages as workflow artifacts. It never publishes a release.

## Known limitations

- The quality of image recognition depends on the host model. The fixtures in this repo are text-based and do not prove recognition accuracy; see [docs/evaluation.md](docs/evaluation.md).
- Different hosts and models may follow the skill differently. Behaviour is not guaranteed to be identical across Claude, Claude Code and Codex.
- Codex plugin installation was not tested in this environment; see [docs/compatibility.md](docs/compatibility.md).
- Category suggestions are human-readable paths, not official Kleinanzeigen category IDs.

## Feedback

Testers' feedback is the most useful input at this stage: so far ReLoopIt has only been tested on synthetic images. Please [open an issue](https://github.com/hashir107/reloopit/issues/new) (you need a free GitHub account) and include:

- the app and model you used (for example "Claude desktop, Opus" or "ChatGPT desktop"),
- what you sent: the item and your one-line note,
- what was wrong or missing, and what you expected.

**Don't attach photos that show personal data**, serial numbers, addresses, documents or people. Describe the photo instead, or crop it first.

## Contributing

Improvements are welcome through pull requests:

1. **Fork** the repository.
2. **Make your change** on a branch and run `python3 scripts/validate.py` and `python3 -m unittest discover -s tests`.
3. **Open a pull request** against `main`.

`main` is protected. Changes land only through a pull request that the owner (@hashir107, see `.github/CODEOWNERS`) has reviewed and approved, and the **validate** check must pass. Direct pushes, force-pushes and deleting `main` are blocked.

## Disclaimer

ReLoopIt is an independent project. It is not affiliated with, endorsed by or connected to Kleinanzeigen. Listing drafts and price suggestions are AI-generated: check every fact before you post, and set the final price yourself. Your photos are processed by the AI app you use (Claude, ChatGPT or Codex) under that provider's terms. ReLoopIt itself has no server and stores nothing.

## License

MIT © 2026 Hashir Rizwan. See [LICENSE](LICENSE).
