# Task 5: Fix Bare Exception Handlers in `ui_iot`

## Context

`services/ui_iot/app.py` has multiple bare `pass` statements in exception handlers at approximately lines 641, 647, 652, 656, 660, and 667. The health check handler (lines ~689-705) also silently catches database errors without logging. These silent failures hide the real state of the system.

## Actions

1. Read `services/ui_iot/app.py` in full, focusing on exception handling blocks.

2. For every `except Exception: pass` or `except Exception:` with no body:
   - Replace `pass` with a meaningful log line at minimum:
     ```python
     except Exception:
         logger.debug("optional step failed, continuing", exc_info=True)
     ```
   - If the exception occurs in a critical code path (auth, database connection, startup), upgrade to `logger.warning` or `logger.error` and add `exc_info=True`.

3. In the health check endpoint (around lines 689-705):
   - Change:
     ```python
     except Exception:
         checks["db"] = "unreachable"
     ```
   - To:
     ```python
     except Exception:
         logger.warning("health check: database unreachable", exc_info=True)
         checks["db"] = "unreachable"
     ```
   - Apply same pattern for other components checked (NATS, Redis if present, etc.).

4. Do not change any business logic.

## Verification

```bash
# No silent pass in except blocks
grep -n 'except.*:\s*$' services/ui_iot/app.py -A1 | grep -E '^\s+pass\s*$'
# Should return zero results
```
