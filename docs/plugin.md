# Claude Code plugin

Assaystone ships a Claude Code plugin marketplace from this repository. The plugin
adds two skills and a Stop hook:

- `/assaystone:audit [claude-code|codex]` audits the newest local session for the
  current repository.
- `/assaystone:setup [warn|block]` scaffolds a contract and CI gate without
  overwriting existing files silently.
- The Stop hook runs `assaystone hook claude-code` after a session and fails open when
  the CLI is absent.

## Install

Inside Claude Code:

```text
/plugin marketplace add yellowsand1/assaystone
/plugin install assaystone@assaystone
```

Install the CLI so the Stop hook can run:

```bash
pip install assaystone
```

Or from a shell:

```bash
claude plugin marketplace add yellowsand1/assaystone
claude plugin install assaystone@assaystone
```

## Local validation

The repository uses Anthropic's validator in CI:

```bash
claude plugin validate ./plugins/assaystone --strict
claude plugin validate . --strict
```

## Files

- `.claude-plugin/marketplace.json` — catalog entry for this repository.
- `plugins/assaystone/.claude-plugin/plugin.json` — plugin metadata.
- `plugins/assaystone/skills/audit/SKILL.md` — one-command session audit.
- `plugins/assaystone/skills/setup/SKILL.md` — contract and hook setup.
- `plugins/assaystone/hooks/hooks.json` — Stop hook declaration.
- `plugins/assaystone/hooks/stop.sh` — fail-open wrapper around the CLI.

## Privacy and limits

Everything runs locally. The plugin does not upload transcripts, source, or test
output. The default Stop hook is warn-only. `tests.integrity` is path-based and reports
test-directory changes, not intent.
