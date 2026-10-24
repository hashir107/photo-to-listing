# Compatibility

**Documentation verified on: 2026-10-21.** Re-check the sources below before each release, because packaging formats change.

## Official sources consulted

| Topic | Source |
| --- | --- |
| Agent Skills format: frontmatter, naming, `references/`, progressive disclosure | https://agentskills.io/specification |
| Spec validator `skills-ref` | https://github.com/agentskills/agentskills/tree/main/skills-ref |
| Claude custom skills: SKILL.md, ZIP packaging (skill folder at top level), upload under Customize > Skills | https://claude.com/docs/skills/how-to |
| Claude Code plugin manifest (`.claude-plugin/plugin.json`, `displayName`, `skills/` layout, `claude plugin validate`) | https://code.claude.com/docs/en/plugins-reference |
| Claude Code marketplace (`.claude-plugin/marketplace.json`, relative `./` sources, reserved names) | https://code.claude.com/docs/en/plugins/marketplace-reference |
| Codex plugins: portable root `plugin.json` with `extensions.com.openai`, `.agents/plugins/marketplace.json`, `codex plugin marketplace add` | https://developers.openai.com/codex/plugins/build |
| Agent Plugins 1.0.0 manifest schema used by Codex | https://agent-plugins.org/schemas/1.0.0/plugin.schema.json |
| Codex skills: `.agents/skills` locations, `$skill` invocation, `/skills` | https://learn.chatgpt.com/docs/build-skills (redirected from developers.openai.com/codex/skills) |
| Codex image input (`codex -i a.png,b.png`, paste in composer, Shift-drag in app or IDE) | https://learn.chatgpt.com/docs/image-inputs |
| Kleinanzeigen "Anzeige aufgeben" form: field order; Titel max. 65; Beschreibung max. 4000; up to 20 images of max. 12 MB | A copy of the form the user saved from kleinanzeigen.de on 2026-10-21. It is not committed because it contains account data. The category-specific "Eigenschaften und Versand" options were **not** visible and remain unverified. |

## Packaging decisions

| Target | Package | Format used | Notes |
| --- | --- | --- | --- |
| Claude (claude.ai and desktop) | `photo-to-listing-skill-v0.4.2.zip` | Archive containing `reloop/SKILL.md` and its resources | Anthropic's guide requires the skill folder as the ZIP's top level, with a name matching `name`. |
| Claude Code | `photo-to-listing-claude-code-v0.4.2.zip` | Local marketplace `photo-to-listing-local` → plugin `photo-to-listing` (`.claude-plugin/plugin.json`, `displayName: ReLoop`) → `skills/reloop/` | The plugin is namespaced, so the skill is `/photo-to-listing:reloop`. |
| Codex | `photo-to-listing-codex-v0.4.2.zip` | Local marketplace `.agents/plugins/marketplace.json` → portable Agent Plugins package with root `plugin.json` and `extensions.com.openai.interface` → `skills/reloop/` | OpenAI recommends the root `plugin.json` for new packages. `.codex-plugin/plugin.json` is a legacy fallback and is not shipped. |

All three contain byte-identical copies of `skills/reloop/`, and `scripts/build_releases.py` verifies this.

**Skill name.** The requested name "ReLoop" contains uppercase letters, which the Agent Skills spec does not allow in `name`. The skill ID is therefore `reloop`. "ReLoop" is used as the display name in Claude Code (`displayName`), in Codex (`interface.displayName`) and in `metadata.display-name`.

**Publisher metadata.** `author`/`owner` are set to the GitHub account `hashir107`, which is the destination you specified. The license is MIT (`LICENSE`, bundled as `skills/reloop/LICENSE.txt`, `"license": "MIT"` in both manifests). No email, privacy-policy or terms URLs are set, because none were provided.

## Host differences

| | Claude (claude.ai and desktop) | Claude Code | Codex |
| --- | --- | --- | --- |
| How photos arrive | Chat attachments | Pasted or dragged images, or file paths the model opens with its Read tool | `-i/--image` flag, pasted into the composer, or Shift-dragged in the app or IDE |
| Install | Upload the ZIP under Customize > Skills | Plugin marketplace or `--plugin-dir` | Plugins Directory (desktop app) after `codex plugin marketplace add`, or copy into `~/.agents/skills` |
| Explicit invocation | By asking; the skill loads when the request matches | `/photo-to-listing:reloop` | `$reloop` or `/skills` |
| Requirements | A plan with Skills and code execution enabled, per Anthropic | Plugins supported in current releases | The desktop app is used to install local plugins, per OpenAI |
| Browsing | Depends on whether web search is enabled | WebSearch/WebFetch tools if allowed | `--search` or the configured web search |

Different models and hosts may follow the same instructions differently. No claim is made that behaviour is identical across them.

## Tested environments and results (2026-10-21)

The installation and image rows below were run on v0.1.0. For v0.2.0 to v0.4.0, the automated checks, `skills-ref`, `claude plugin validate` and the image re-run were repeated (see [evaluation.md](evaluation.md)). The `claude plugin install` test was not repeated, because the package layout did not change.

| Check | Environment | Result |
| --- | --- | --- |
| `scripts/validate.py`, unit tests (46 in v0.1.0, 52 in v0.2.0, 59 in v0.3.0, 63 in v0.4.0, 66 in v0.4.1), reproducible build | macOS 26 (Darwin 25.6.0), Python 3.14.8 | Pass |
| Same, in CI | GitHub Actions `ubuntu-latest`, Python 3.12 | See the workflow runs on the repository |
| `skills-ref validate` on source, Claude ZIP and Codex package skill | skills-ref 0.1.0 (commit `69ef37e`) | `Valid skill` ×3 |
| Schema meta-validation and examples | jsonschema 4.26.0 (Draft 2020-12) | Pass |
| Codex `plugin.json` against the Agent Plugins 1.0.0 schema | jsonschema 4.26.0 | 0 errors |
| `claude plugin validate` on marketplace and plugin (`--strict`) | Claude Code 2.1.292 | `✔ Validation passed` for both |
| **Actual install**: `claude plugin marketplace add` and `claude plugin install photo-to-listing@photo-to-listing-local` from the unzipped package | Claude Code 2.1.292, isolated `CLAUDE_CONFIG_DIR` | Installed, enabled, version 0.1.0. `claude plugin details` lists skill `reloop` (~150 tokens always on, ~1.7k on invoke) |
| Headless skill run via `claude -p --plugin-dir …` | Claude Code 2.1.292 | **Not run.** The standalone CLI on the test machine was not logged in, and credentials were not entered on the user's behalf. |
| Image run that follows the packaged SKILL.md | Claude Code desktop subagent (Claude Opus 5.5), 2 synthetic images | See [evaluation.md](evaluation.md). The skill was loaded by hand, not through plugin activation. |
| Claude ZIP upload (Customize → Skills) | User's Claude account | **v0.1.0 accepted**: after the user uploaded it, the skill appeared in their account's skill list (observed 2026-10-23). Later versions use the same ZIP layout but have not been uploaded yet. Mobile availability has not been verified. |
| Skill folder in `~/.agents/skills/reloop` | ChatGPT desktop app (macOS) | **Works, as reported by the user** (2026-10-24, v0.4.0) |
| Skill folder in `~/.agents/skills/reloop` | Codex CLI / IDE extension | **Not tested.** Codex CLI is not installed on the test machine; this uses the same documented skill location as the ChatGPT desktop app. |
| Codex plugin via local marketplace | — | **Not tested.** The manifest is validated against the official Agent Plugins schema only. |

## Untested assumptions and limitations

- Codex: it is assumed that `codex plugin marketplace add` accepts the unzipped folder as a local marketplace root, and that the Plugins Directory lists the plugin. Both follow the documentation but were not verified.
- Claude.ai: it is assumed that the upload accepts a ZIP that also contains `examples/` and `schema.json` next to `references/`. The documentation allows arbitrary extra files.
- Activation reliability, meaning how often each host picks the skill on its own, was not measured. Explicit invocation is the fallback.
