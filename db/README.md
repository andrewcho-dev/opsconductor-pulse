# Database Migrations

See [docs/operations/database.md](../docs/operations/database.md) for the complete migration index, schema overview, and database operations guide.

## Quick Reference

```bash
# Apply all pending migrations (idempotent)
python db/migrate.py

# Apply a specific migration manually
psql "$DATABASE_URL" -f db/migrations/NNN_name.sql
```
