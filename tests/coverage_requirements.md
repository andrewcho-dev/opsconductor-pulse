# Coverage Requirements

## Minimum Thresholds

| Component | Minimum Coverage |
|-----------|------------------|
| Overall | 70% |
| Critical paths | 90% |

## Critical Paths (require 90%+)

These modules handle security and tenant isolation:

- `services/ui_iot/middleware/auth.py`
- `services/ui_iot/middleware/tenant.py`
- `services/ui_iot/db/pool.py`
- `services/ui_iot/utils/url_validator.py`

## Exemptions

These files are excluded from coverage:

- `*/migrations/*` - Database migrations
- `*/tests/*` - Test files themselves
- `*/__pycache__/*` - Compiled Python

## Enforcement

- CI fails if coverage drops below 70%
- PRs must not decrease coverage
- New code must have tests
