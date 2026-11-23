# Field note: what 162 real Claude Code sessions say about verification

*November 2026. Local corpus, aggregate-only, no prompts or project paths.*

We ran a read-only aggregate audit over 162 usable Claude Code sessions from a local
corpus (167 transcript files, ~578 MB). The goal was simple: does the audit find
signals in real sessions, and where does it go blind?

Method: load each transcript, reconstruct the files touched by `Write` / `Edit` /
`MultiEdit`, and run the default path/config rules. Bash file writes were measured
separately. The corpus is one user's sessions, with no human labels; the numbers are
**signals**, not confirmed defects.

## Results

| Metric | Value |
|---|---|
| Usable sessions | 162 |
| Steps | 28,082 |
| Reconstructed artifacts | 858 |
| Sessions with Edit/Write edits | 63 (39%) |
| Sessions with test-file edits | 28 (17%; 44% of editing sessions) |
| Sessions with **only** test edits | 1 |
| Sessions with debug prints | 9 (23 files) |
| Sessions with forbidden-path edits | 2 (10 files) |
| Sessions with any path/policy signal | 35 (22%; 56% of editing sessions) |
| Sessions over 200 steps | 46 (28%) |
| Step median / p90 / max | 96 / 347 / 2,440 |

Tool distribution: `Bash` 20,688, `Edit` 3,114, `Read` 2,931, `Write` 563. Bash is
about 74% of all steps.

## What the data says

**1. Test edits dominate, but test tampering is rare.** 28 sessions touched test
files; 27 also touched source files, which is normal feature work. Only one session
edited tests without touching source — the strongest tampering candidate. This is why
the Stop hook defaults to `warn`, not `block`, and why ignore rules matter.

**2. Bash is the audit's blind spot.** 61 sessions wrote files through Bash
(`cat >`, `tee`, `sed -i`, `patch`, `perl -pi`, `git apply`, ...). 16 of those had
**no Edit/Write artifacts at all**, and 4 wrote to test paths. The 35 signals are a
lower bound; transcript replay covers the editor, not the shell.

**3. A 200-step budget is too tight.** 46/162 sessions (28%) exceeded 200 steps; p90
was 347 and the max was 2,440. A 200-step guard would flag ordinary long sessions as
noise.

**4. "All tests pass" is rare.** A strict claim check found zero sessions. Real final
messages are summaries, not acceptance claims; the useful signals are path/config/state
changes, not self-report contradictions.

## Manual triage: the five strongest candidates

We inspected the five unique candidates (1 test-only, 4 Bash test writes). **Zero
confirmed test tampering.**

- Three Bash "test write" flags were temporary probe scripts or delivery notes whose
  contents/imports mentioned test paths; the written file was outside the repo test
  tree.
- One test-only session was a test fixture/schema refactor during an upstream bug
  investigation (the task explicitly asked to check for and add tests); it deleted and
  modified fixture classes and SQL, not assertions in the surviving test.
- One Bash session added new Java test files (new tests), not removed or weakened
  tests.

Takeaway: path-based `tests.integrity` surfaces **test-directory activity, not
intent**. The Stop hook's warn-first default is correct; an intent-aware verifier
should compare removed test functions/assertions against a pre-image.

## Changes shipped in 0.3.1

- The Claude Code hook now merges **git working-tree changes** when `cwd` is the git
  root, so Bash-made edits are audited too. Non-git workspaces still use transcript
  artifacts.
- The audit's default step budget moved from 200 to **5,000** (a runaway-loop guard,
  not an acceptance criterion).
- `scripts/corpus_audit.py` reproduces this style of aggregate corpus audit:
  ```bash
  python scripts/corpus_audit.py --root ~/.claude/projects
  python scripts/corpus_audit.py --json --max-files 50
  ```

## Limits

- Single-user corpus, no human labels; treat everything as a signal.
- Transcript replay only sees `Write` / `Edit` / `MultiEdit`; Bash coverage depends on
  git working-tree changes.
- Sessions with no edits may still have Bash writes; the corpus script reports that
  gap separately.
- Repos without a `HEAD` commit cannot use the git pre-image path.
