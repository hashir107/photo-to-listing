# ReLoop for Claude Code: photo-to-listing v{{VERSION}}

This package holds a local plugin marketplace (`.claude-plugin/marketplace.json`). It lists one plugin, `photo-to-listing`, which contains the `reloop` skill.

```
photo-to-listing-claude-code-v{{VERSION}}/
├── .claude-plugin/marketplace.json
└── plugins/photo-to-listing/
    ├── .claude-plugin/plugin.json
    └── skills/reloop/…
```

## Install (persistent)

From the folder where you unzipped the package:

```bash
claude plugin marketplace add ./photo-to-listing-claude-code-v{{VERSION}}
claude plugin install photo-to-listing@photo-to-listing-local
```

Or inside a Claude Code session:

```
/plugin marketplace add ./photo-to-listing-claude-code-v{{VERSION}}
/plugin install photo-to-listing@photo-to-listing-local
```

Start a new session afterwards so the skill is listed.

## Try without installing

```bash
claude --plugin-dir ./photo-to-listing-claude-code-v{{VERSION}}/plugins/photo-to-listing
```

## Use

- Give Claude Code the photos. You can paste an image into the prompt, drag a file in, or reference image paths, for example `Draft a Kleinanzeigen listing from ./photos/1.jpg and ./photos/2.jpg`.
- Add an optional one-line note, for example "24 LG monitors, office closing."
- The skill activates on matching requests. You can also invoke it explicitly with `/photo-to-listing:reloop`.
- Answer the follow-up questions in later messages; the result is updated in place.

## Remove

```bash
claude plugin uninstall photo-to-listing@photo-to-listing-local
claude plugin marketplace remove photo-to-listing-local
```

## Check the package yourself

```bash
claude plugin validate ./photo-to-listing-claude-code-v{{VERSION}}
claude plugin validate ./photo-to-listing-claude-code-v{{VERSION}}/plugins/photo-to-listing
```
