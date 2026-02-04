## Required Status Checks

The following checks must pass before merging to main:

- **Unit Tests** — all unit tests pass (no infrastructure required)
- **Integration Tests** — all integration tests pass with coverage enforcement
- **E2E Tests** — all end-to-end browser tests pass
- **Lint** — ruff check and format check pass

## Coverage Requirements

- Overall: 60% minimum (enforced by check_coverage.py)
- Critical modules: 85-90% (auth.py, tenant.py, pool.py, url_validator.py)

## Performance Benchmarks

- Run on main pushes (not PRs)
- Results uploaded as artifacts for tracking
- Not blocking — used for trend analysis
# Branch Protection Settings

Configure these settings in GitHub repository settings:

## Main Branch Protection

1. Go to Settings > Branches > Add rule
2. Branch name pattern: `main`
3. Enable:
   - [x] Require a pull request before merging
   - [x] Require status checks to pass before merging
     - Required checks:
       - `Unit Tests`
       - `Integration Tests`
       - `Lint`
   - [x] Require branches to be up to date before merging
   - [x] Do not allow bypassing the above settings

## Develop Branch Protection (if used)

1. Branch name pattern: `develop`
2. Enable:
   - [x] Require status checks to pass before merging
     - Required checks:
       - `Unit Tests`
       - `Integration Tests`
