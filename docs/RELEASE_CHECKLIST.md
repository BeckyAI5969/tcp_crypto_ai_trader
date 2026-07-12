# Release v0.1.0 Checklist

## Repository
- [ ] `git status` shows a clean working tree
- [ ] `.env` is not tracked
- [ ] No API keys or secrets are committed
- [ ] GitHub Actions is green

## Quality
- [ ] `py -B -m compileall src` passes
- [ ] `py -B -m compileall tests` passes
- [ ] `py -B -m unittest discover -s tests -v` passes
- [ ] Main pipeline runs successfully in PAPER mode
- [ ] Structured logs are created

## Safety
- [ ] `TCP_EXECUTION_MODE=PAPER`
- [ ] `TCP_ALLOW_LIVE_TRADING=false`
- [ ] Testnet order submission remains disabled
- [ ] Live trading remains disabled

## Release Commands

```powershell
git add CHANGELOG.md docs/ARCHITECTURE.md CONTRIBUTING.md docs/RELEASE_CHECKLIST.md
git commit -m "Release v0.1.0: add release documentation"
git push

git tag -a v0.1.0 -m "TCP Crypto AI Trader v0.1.0"
git push origin v0.1.0
```
