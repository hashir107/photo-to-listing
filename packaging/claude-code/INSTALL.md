# ReLoopIt for Claude Code: reloopit v{{VERSION}}

This package holds a local plugin marketplace (`.claude-plugin/marketplace.json`). It lists one plugin, `reloopit`, which contains the `reloopit` skill.

```
reloopit-claude-code-v{{VERSION}}/
├── .claude-plugin/marketplace.json
└── plugins/reloopit/
    ├── .claude-plugin/plugin.json
    └── skills/reloopit/…
```

## Install (persistent)

From the folder where you unzipped the package:

```bash
claude plugin marketplace add ./reloopit-claude-code-v{{VERSION}}
claude plugin install reloopit@reloopit-local
```

Or inside a Claude Code session:

```
/plugin marketplace add ./reloopit-claude-code-v{{VERSION}}
/plugin install reloopit@reloopit-local
```

Start a new session afterwards so the skill is listed.

## Try without installing

```bash
claude --plugin-dir ./reloopit-claude-code-v{{VERSION}}/plugins/reloopit
```

## Use

- Give Claude Code the photos. You can paste an image into the prompt, drag a file in, or reference image paths, for example `Draft a Kleinanzeigen listing from ./photos/1.jpg and ./photos/2.jpg`.
- Add an optional one-line note, for example "24 LG monitors, office closing."
- The skill activates on matching requests. You can also invoke it explicitly with `/reloopit:reloopit`.
- Answer the follow-up questions in later messages; the result is updated in place.

## Remove

```bash
claude plugin uninstall reloopit@reloopit-local
claude plugin marketplace remove reloopit-local
```

## Check the package yourself

```bash
claude plugin validate ./reloopit-claude-code-v{{VERSION}}
claude plugin validate ./reloopit-claude-code-v{{VERSION}}/plugins/reloopit
```
