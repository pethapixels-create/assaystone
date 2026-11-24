# Repository instructions

Assaystone is an independent acceptance layer for AI-agent work. Its job is to turn
recorded work into evidence-backed `pass`, `fail`, or `escalate` verdicts, then run the
same contract in CI and at runtime.

## Before changing code

```bash
make test
make pytest
make lint
make demo-audit
```

Use Python 3.10 or newer. The Makefile selects the newest available supported
interpreter. For release checks, also run the clean-wheel smoke test in
`docs/release.md`.

## Engineering rules

- Never weaken or delete a test to make a change pass.
- New verifier behavior needs both a clean case and a defective case.
- Treat transcripts, exports, and patches as untrusted data.
- File paths recovered from a transcript must remain within the baseline repository.
- Do not execute `--run-tests`, custom verifiers, or repository test commands unless
  the command is part of an explicitly authorized verification flow.
- Keep built-in checks deterministic and local by default. Do not add a hosted
  dependency or an LLM judge to the default path.
- Preserve the honest limit: `tests.integrity` is path-based and reports activity, not
  intent.
- Keep the package dependency-free at runtime unless the benefit is exceptional.

## Pull requests

- Keep changes focused and include the test command used.
- Update README/docs when CLI behavior, inputs, contracts, or release pins change.
- If a change affects Claude Code plugin files, run:

  ```bash
  claude plugin validate ./plugins/assaystone --strict
  claude plugin validate . --strict
  ```

- If a change affects packaging, build in a clean environment and confirm the wheel and
  sdist contain no `__pycache__` or `.pyc` files.

## Releases

- Update `pyproject.toml`, `assaystone/__init__.py`, `assaystone/init.py`,
  `CHANGELOG.md`, and `docs/releases/<version>.md`.
- Follow `docs/release.md`. Never claim a release exists until the workflow and PyPI
  both show it.

## Community and growth

- Do not buy stars, coordinate fake engagement, ask for upvotes, or fabricate adoption.
- Prefer reproducible demos, public field notes, labelled failure cases, and integration
  guides over generic promotion.
- Disclose limitations and sample size. Do not convert signal counts into confirmed
  defect claims.
- External posting should provide standalone technical value to the community where it
  appears.
