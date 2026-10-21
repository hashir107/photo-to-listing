# ReLoop for Codex: photo-to-listing v{{VERSION}}

This package holds a local plugin marketplace (`.agents/plugins/marketplace.json`). It lists one portable Agent Plugins package, `photo-to-listing`, which contains the `reloop` skill.

```
photo-to-listing-codex-v{{VERSION}}/
├── .agents/plugins/marketplace.json
└── plugins/photo-to-listing/
    ├── plugin.json            # Agent Plugins 1.0.0 manifest with extensions.com.openai
    └── skills/reloop/…
```

## Option A: install the plugin from this local marketplace

1. Register the marketplace root, which is the unzipped folder:

   ```bash
   codex plugin marketplace add ./photo-to-listing-codex-v{{VERSION}}
   codex plugin marketplace list
   ```

2. Open the Plugins Directory in Codex in the ChatGPT desktop app. Choose **photo-to-listing (local)** and install **ReLoop**. OpenAI's documentation says to use the desktop app to install and test local plugins. Restart the app if the marketplace does not appear.

To turn the plugin on or off for one project, add this to that project's `.codex/config.toml`:

```toml
[plugins."photo-to-listing@photo-to-listing-local"]
enabled = true
```

## Option B: install only the skill (Codex CLI, IDE extension or app)

Copy the skill folder into a skills location that Codex scans, then restart Codex:

```bash
mkdir -p ~/.agents/skills
cp -R ./photo-to-listing-codex-v{{VERSION}}/plugins/photo-to-listing/skills/reloop ~/.agents/skills/reloop
```

Use `<repo>/.agents/skills/reloop` instead to scope the skill to one repository.

## Use

- Attach the photos. In the CLI, run `codex -i photo1.jpg,photo2.jpg "Draft a Kleinanzeigen listing. Note: 24 LG monitors, office closing."` or paste images into the composer. In the app, drag images into the composer while holding Shift.
- Invoke the skill explicitly with `$reloop`, or pick it from `/skills`. Codex may also select it on its own when a request matches its description.
- Answer the follow-up questions in later messages; the result is updated in place.

## Remove

```bash
codex plugin marketplace remove photo-to-listing-local
rm -rf ~/.agents/skills/reloop   # only if you used option B
```
