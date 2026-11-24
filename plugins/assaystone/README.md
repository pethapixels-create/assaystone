# Assaystone Claude Code plugin

This plugin exposes Assaystone inside Claude Code:

- `/assaystone:audit [claude-code|codex]` audits the newest local session for the
  current repository.
- `/assaystone:setup [warn|block]` installs an acceptance contract and CI gate.
- A Claude Code `Stop` hook runs the audit after a session when the `assaystone` CLI is
  installed. It fails open when the CLI is missing or the audit cannot run.

## Install

```bash
claude plugin marketplace add yellowsand1/assaystone
claude plugin install assaystone@assaystone
```

Install the CLI so the Stop hook can run:

```bash
pip install assaystone
```

Everything runs locally. No transcript, source code, or test output is uploaded.
See the [main README](https://github.com/yellowsand1/assaystone) for audit rules and
limitations.
