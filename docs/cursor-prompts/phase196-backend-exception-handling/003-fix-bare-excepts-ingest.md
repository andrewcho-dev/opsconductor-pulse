# Task 3: Fix Bare Exception Handlers in `ingest_iot`

## Context

`services/ingest_iot/ingest.py` contains multiple `except Exception:` blocks that either `pass` silently or log a warning and continue. Some of these may be masking fatal errors (pool exhaustion, OOM, unexpected API changes).

## Actions

1. Read `services/ingest_iot/ingest.py` in full.

2. For each `except Exception:` block, determine the intent:

   **Pattern A — Expected, recoverable per-message error** (e.g., malformed payload, unknown device):
   - Keep the broad catch but add specific logging. Replace silent `pass` with:
     ```python
     except Exception:
         logger.warning("failed to process message", exc_info=True, extra={"context": "..."})
     ```

   **Pattern B — Infrastructure error** (database connection failure, NATS disconnect, OOM):
   - These should NOT be silently swallowed. Use:
     ```python
     except (asyncpg.PostgresConnectionError, asyncpg.TooManyConnectionsError):
         logger.error("database connection failed", exc_info=True)
         raise  # Let the caller handle or crash the worker
     except MemoryError:
         logger.critical("out of memory", exc_info=True)
         raise
     except Exception:
         logger.error("unexpected error in ingest worker", exc_info=True)
         raise  # Do not silently continue on unknown errors
     ```

   **Pattern C — Truly ignorable** (e.g., optional metric enrichment that failing doesn't break ingest):
   - Keep the catch but document WHY it's safe to ignore:
     ```python
     except Exception:
         # Safe to ignore: enrichment is optional; core telemetry was already written
         logger.debug("optional enrichment failed", exc_info=True)
     ```

3. Apply the appropriate pattern to each handler. Prioritize correctness over brevity.

4. Do not change any business logic — only the exception handling strategy.

## Verification

```bash
grep -n 'except Exception' services/ingest_iot/ingest.py
# Each remaining occurrence should have a comment explaining why the broad catch is intentional
```
