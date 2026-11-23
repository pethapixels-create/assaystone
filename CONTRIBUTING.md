# Contributing

The fastest way to help is to bring a real failure case.

## Bring a failure case

If an agent produced output that looked acceptable but was not, open an issue with the
`failure case` template. Redact secrets, attach the trace JSON if you can, and state
the human verdict and which check should have caught it. Accepted cases go into the
[Failure Zoo](failure_zoo/README.md) and become regression tests.

## Add a verifier

A verifier is a small class with a declared layer, cost, and independence.

```python
from assaystone import Verifier, register

@register
class NoMigrationEdits(Verifier):
    name = "policy.no_migrations"
    layer = "L1"
    cost_usd = 0.00001
    independence = "high"
    description = "Agents must not edit migrations."

    def check(self, ctx, params):
        bad = [path for path, _ in ctx.changed() if path.startswith("migrations/")]
        return (not bad, [f"migration touched: {path}" for path in bad], [])
```

Requirements:

- Return `(ok, reasons, evidence)`. `ok=None` means "cannot decide" and escalates.
- Prefer deterministic evidence from artifacts, tool results, or the environment.
- Declare an honest `cost_usd`; the runner uses it to order checks.
- Add a test that proves the verifier kills a known defect and passes a clean run.
- Do not use an LLM judge as an oracle.

To ship a verifier as a third-party pack, expose a module that imports your
`@register` classes and add an entry point:

```toml
[project.entry-points."assaystone.verifiers"]
mypack = "mypack.verifiers"
```

Assaystone loads installed packs at import time; a broken pack is ignored.

## Add an adapter

Adapters live in `assaystone/adapters/`. They must be duck-typed and must not import
the framework. Add a test with recorded messages, not a live API call.

## Development

```bash
python3 -m unittest discover -s tests -t . -v
make demo
```

No runtime dependencies. Python 3.10+.

## Pull request checklist

- [ ] Tests pass (`make test`).
- [ ] The demo still runs (`make demo`).
- [ ] New verifiers have a layered test (clean + defective).
- [ ] Docs updated if the contract or trace format changed.
- [ ] No secrets or customer data in fixtures.

## Code of conduct

Be direct, be kind, assume good faith. Harassment is not welcome.
