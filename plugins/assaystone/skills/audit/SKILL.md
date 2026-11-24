---
name: audit
description: Audit the most recent Claude Code or Codex session for silent failures, test tampering, forbidden edits, unsupported success claims, and other acceptance-contract violations. Use when the user asks to check what an agent actually did, verify that a coding-agent run is trustworthy, or investigate a green test suite that may be hiding a bad change.
argument-hint: "[claude-code|codex]"
---

# Audit the latest agent run

1. Use the optional argument as the agent name. Default to `claude-code`; accept `codex`.
2. From the current repository root, run:

   ```bash
   assaystone audit --latest <agent>
   ```

   If `assaystone` is not installed, run the same command through `uvx assaystone ...`.
3. Report the findings in severity order. Include the changed files, verifier name, and the concrete reason. Never present a path-based `tests.integrity` finding as proof of intent; explain that it flags test-directory activity.
4. If the audit returns no findings, say what was checked and note that this is not proof the agent's work is correct.
5. If findings exist, suggest the exact next command:

   ```bash
   assaystone audit --latest <agent> --write-contract .assaystone/contract.json
   ```

   Do not run `--run-tests` or execute repository code unless the user asks.
