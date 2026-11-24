---
name: setup
description: Set up Assaystone acceptance contracts and CI gating for the current repository. Use when the user wants to add an automated verification gate for AI-agent changes, install the Claude Code Stop hook, or scaffold a contract.
argument-hint: "[warn|block]"
---

# Set up Assaystone

1. Inspect the repository for an existing `.assaystone/contract.json` and existing
   Assaystone GitHub Actions workflow. Do not overwrite either without explicit user
   permission.
2. Create the contract without guessing the repository's test command:

   ```bash
   assaystone init --ci
   ```

   If `assaystone` is not installed, use `uvx assaystone init --ci`.
3. Read the generated contract and confirm that its protected paths and test command
   match the repository. Report any warning from the command.
4. Install the Claude Code Stop hook. Use `warn` unless the user explicitly requests
   `block`:

   ```bash
   assaystone hook install claude-code --mode warn
   ```

5. Explain that `block` can interrupt sessions and that `--run-tests` executes project
   code in a temporary copy, not a sandbox.
