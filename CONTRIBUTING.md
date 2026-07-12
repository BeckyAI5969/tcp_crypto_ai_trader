# Contributing

## Development Rules

1. Work on a dedicated branch.
2. Keep the default execution mode as `PAPER`.
3. Never commit `.env`, API keys, API secrets, or credentials.
4. Compile and test before every commit.
5. Do not enable live trading in source code.
6. Keep changes small and reversible.

## Local Quality Checks

Run from the repository root:

```powershell
py -B -m compileall src
py -B -m compileall tests
py -B -m unittest discover -s tests -v
git status
git ls-files .env
```

Expected result:
- Compilation succeeds
- Tests report `OK`
- `.env` is not listed
- Working tree is clean before tagging

## Commit Style

Examples:

```text
Sprint 23: add release documentation
Fix: correct position sizing validation
Test: add low-confidence rejection case
```

## Pull Request Checklist

- [ ] Code compiles
- [ ] Tests pass
- [ ] No secrets are committed
- [ ] Logging does not expose sensitive values
- [ ] PAPER mode remains the default
- [ ] Documentation is updated
