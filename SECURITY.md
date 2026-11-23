# Security policy

## Supported versions

Security fixes land on `main` and in the latest PyPI release. Older releases may not
receive backports.

## Reporting a vulnerability

Please report vulnerabilities privately through
[GitHub Security Advisories](https://github.com/yellowsand1/assaystone/security/advisories/new).
Do not open a public issue for a suspected vulnerability.

Include the version, a minimal reproduction, and the impact. We will acknowledge the
report and coordinate disclosure.

## Threat model

Assaystone parses untrusted transcripts and runs local verification commands.

- **Transcripts are data.** JSONL/JSON parsing does not execute agent output. Do not
  point the audit at a transcript you would not open in a text editor.
- **`--run-tests` is not a sandbox.** It runs the project's test command inside a
  temporary copy of the baseline. Only use it with repositories and contracts you
  trust. The same applies to custom verifiers and test commands.
- **The Claude Code hook is fail-open.** If the audit cannot run, the session is not
  blocked by default. Review `.assaystone/hook.json` before using `--mode block`.
- **No telemetry or network calls by default.** Importers read local export files.
- **Reports can contain code.** Evidence includes snippets and test output. Use
  `--no-evidence` for machine reports that leave your machine.

## Secrets and private data

Do not commit transcripts, traces, or contracts containing secrets, customer data, or
private project paths. Redact them before sharing a Failure Zoo case.
