# Contributing to ufme

Thanks for your interest! Issues and pull requests are welcome.

## Before you start

- For anything bigger than a bug fix, open an issue first so we can agree on the approach.
- By submitting a contribution you agree that it is licensed under the project's
  [Apache License 2.0](LICENSE) (section 5 of the license), and you confirm you have the right to submit it.
  Please sign off your commits (`git commit -s`, the [Developer Certificate of Origin](https://developercertificate.org/)).

## Development setup

Everything runs in Docker; see the Quick start in the [README](README.md).

```bash
docker compose -f infra/docker/docker-compose.yml --profile test run --rm api-test   # backend checks
docker compose -f infra/docker/docker-compose.yml --profile test run --rm web-test   # frontend build
```

## Pull request checklist

- Backend: `ruff check`, `ruff format`, `mypy app` and `pytest` pass (the api-test container runs all four).
- Matching changes: the benchmark floors still pass (`benchmarks/floor_*_engine.json`); don't lower a floor
  without explaining why in the PR.
- New tables with tenant data have a `tenant_id` column (row-level security is applied automatically; the
  security tests check it).
- No real customer data, credentials or secrets in code, tests or fixtures.
- Keep UI text in plain business language.

## Code of conduct

Be respectful and constructive. Harassment or personal attacks are not tolerated.
