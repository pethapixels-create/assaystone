# Launch and adoption plan

Stars are a lagging indicator of usefulness. Optimize for the first ten minutes, for
embedding in real workflows, and for giving people a reason to contribute a case.

## Position

Assaystone audits AI agent traces for silent failures. Point it at a Claude Code
transcript; it reconstructs the changed files and reports test tampering, forbidden
paths, debug prints, and self-report contradictions. When you find something, turn it
into an acceptance contract and gate CI and runtime with the same checks.

Not an agent framework. Not another eval leaderboard. Not an LLM-judge wrapper.

## Hooks

- "Point it at a Claude Code transcript; it finds the test the agent deleted."
- "Your agent's tests pass. Did it delete the failing test?"
- "Evals give you a score. Production needs a verdict."
- "The stricter contract caught 4/4 defects and cost less than the naive one."

## Assets to produce before launch

1. A 60-second terminal recording of `python3 -m assaystone demo audit` (the single
   most important asset; put it at the top of the README).
2. A recording of the Claude Code Stop hook: one `assaystone hook install` command, a
   finding, and a blocked stop with `--mode block`.
3. A recording of `python3 -m assaystone demo` (code contract comparison + mutation).
4. A recording of `python3 -m assaystone demo ops` (runtime gate blocking a denied
   approval and an over-limit refund).
5. A real audit: your own transcript, or a public coding-agent trajectory.
6. A screenshot or Markdown copy of the scorecards.
7. Three copy-paste integrations: pytest, GitHub Action, Claude Agent SDK adapter.
8. The essay in `docs/why.md` as a standalone post.
9. A one-page "what it catches that tests miss" table.

## Sequence

**T-7 days**

- Publish the repo and the first PyPI release.
- CI green; `make test`, `make demo`, `make demo-ops`, and `make demo-audit` pass on
  Python 3.10–3.12.
- Finish the README hook, quickstart, comparison table, and issue templates.
- Seed the Failure Zoo with the demo traces.
- Ask five agent teams to run `assaystone audit` on a real transcript and report the
  first false alarm.

**T-0**

- Show HN, X thread, Reddit (`r/LocalLLaMA`, `r/MachineLearning`), AI Engineer
  communities.
- Lead with the failure story, not the feature list. Post the demo output as text in
  the first comment.
- Ask for failure cases, not stars.

**T+1 week**

- Answer every issue within a day; turn each reproduction into a regression case.
- Submit adapter PRs to one or two agent frameworks.
- Pitch one newsletter / podcast with the "verification is the bottleneck" essay.

**T+1 month**

- Publish a small benchmark: "we mutation-tested N agent traces; here is what LLM
  judges missed."
- Ship the first external verifier pack (data reconciliation or report citations).
- Announce the Failure Zoo leaderboard for verifier recall.

## Repository settings

GitHub About:

> Audit AI agent traces for silent failures — deleted tests, forbidden edits,
> unsupported claims — then turn findings into acceptance contracts for CI and
> runtime. Claude Code / LangSmith / Langfuse / OTel input. Mutation testing and
> backtesting included.

Topics: `ai-agents`, `llm`, `evaluation`, `verification`, `testing`,
`mutation-testing`, `pytest`, `github-actions`, `python`.

Pin these four issues as `good first issue`:

1. Add an OpenAI Agents SDK guardrail adapter.
2. Add a LangGraph callback wrapper.
3. Add a git pre-image baseline for post-session diff checks.
4. Add a Failure Zoo benchmark runner and leaderboard.

## Channels

- Hacker News (Show HN) — best for the contrarian "your eval is lying" framing.
- X / LinkedIn — the scorecard and the one-line hook travel well.
- Reddit — technical depth; link the essay, not the repo.
- AI engineering newsletters — the benchmark and the essay.
- Framework communities (Claude, OpenAI Agents, LangGraph) — adapter demos.

## Growth loops

1. **`assaystone audit`** — one command on a trace gives value before a contract; this
   is the acquisition loop.
2. **Claude Code Stop hook** — `assaystone hook install claude-code` puts the audit
   in every session.
3. **`assaystone init`** — one command in any repo produces a contract; retention.
4. **pytest plugin** — every adoption puts a contract in someone's CI.
5. **GitHub Action** — failures show up as PR annotations; reviewers see the product.
6. **Failure Zoo** — every contributed failure becomes a fixture and a story.
7. **Verifier registry** — domain packs accumulate; contributors become maintainers.
8. **Shareable scorecards** — teams paste them into PRs and design docs.

## Metrics

- PyPI installs and weekly active repositories (hard to measure; ask in issues).
- Number of external verifiers and adapters.
- Failure Zoo contributions and accepted cases.
- CI integrations (GitHub Action usage).
- Stars — track, but do not optimize directly.

## What not to do

- Do not position as "yet another eval framework."
- Do not gate the core behind a hosted service.
- Do not build a dashboard before the CLI is loved.
- Do not chase every framework; start with Claude Agent SDK and OpenAI-style
  messages.
- Do not publish numbers you cannot reproduce.

## Show HN draft

**Title:** Show HN: Assaystone – find the test your coding agent deleted

**First comment:**

We kept seeing the same failure in coding agents: the suite goes green because the
agent deleted the failing test. Evals scored the run as a success. The patch was not
acceptable.

Assaystone is an audit + verification layer. Point it at a Claude Code transcript and
it reconstructs the changed files, runs a default rule set, and reports findings with
evidence. `python3 -m assaystone demo audit` shows it catching a deleted test.

It also accepts LangSmith, Langfuse, and OpenTelemetry exports. And there is a Claude
Code Stop hook:
one settings entry, and every session is audited when the agent stops. It warns by
default; `ASSAYSTONE_HOOK_MODE=block` enforces.

When you find a failure, turn the findings into an acceptance contract. The same
contract runs in CI (pytest / GitHub Action) and at runtime (approval gates for
irreversible tools). Mutation testing and backtesting prove the checks work.

The code demo compares a naive contract (`tests + syntax`) with a hardened one:
1/4 vs 4/4 defects caught, and mutation testing raises verifier recall from 67% to
94%. The ops demo catches 0/4 vs 4/4 bad refunds, and the runtime gate blocks a denied
approval and an over-limit refund.

No API keys, no dependencies: `python3 -m assaystone demo audit`,
`python3 -m assaystone demo`, and `python3 -m assaystone demo ops`.

We are looking for failure cases, verifier proposals, and framework adapters. If your
agent has shipped something that looked fine and was not, we would like the trace.
