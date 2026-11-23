# Claude Code Stop hook

Runs `assaystone audit` on the session transcript when Claude stops. Default is
`warn`; `block` stops the turn for high/critical findings.

## Install

```bash
pip install assaystone
cd your-agent-repo
assaystone hook install claude-code --mode warn
```

This merges the hook into `.claude/settings.local.json` (project scope). Use
`--user` for `~/.claude/settings.json`, and `--mode block` to enforce. Restart Claude
Code so it loads the settings.

The equivalent settings entry is:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {"type": "command", "command": "assaystone hook claude-code"}
        ]
      }
    ]
  }
}
```

## Tune

Copy `hook.json` to `.assaystone/hook.json` in the repository:

```json
{
  "mode": "warn",
  "fail_on": "high",
  "ignore": [
    {"verifier": "tests.integrity", "paths": ["server/tests/**"]}
  ]
}
```

- `mode`: `warn` or `block`.
- `fail_on`: `none`, `high`, or `any`.
- `ignore`: filter findings by verifier, changed-path glob, or reason substring.

Environment variables `ASSAYSTONE_HOOK_MODE` and `ASSAYSTONE_HOOK_FAIL_ON` override
the file.

## Behavior

- Reads `transcript_path`, `cwd`, and `stop_hook_active` from stdin.
- Reads the current files touched by `Write` / `Edit` / `MultiEdit` (workspace mode —
  the tree is post-session).
- Warn mode reports an identical finding once per session; dedupe state lives under
  `$XDG_CACHE_HOME/assaystone/hooks/`.
- Block mode exits `2` for high/critical findings; `stop_hook_active` prevents a loop.
- Audit failures fail open with a message.

Start in `warn` mode: legitimate tasks edit tests. Watch the findings, add ignore
rules for known-good edits, then switch to `block`.

## Test manually

```bash
echo '{"transcript_path": "/path/to/session.jsonl", "cwd": "/path/to/repo"}' \
  | ASSAYSTONE_HOOK_MODE=block assaystone hook claude-code
```

The transcript path can be absolute or relative to `cwd`.
