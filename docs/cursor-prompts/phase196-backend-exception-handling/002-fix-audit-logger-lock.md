# Task 2: Fix Audit Logger Lock Contention

## Context

`services/shared/audit.py:154-176`: The audit logger acquires `self._lock`, then performs `await conn.copy_records_to_table(...)` while holding it. This means the lock is held during a database write — blocking any other coroutine that tries to add an audit event.

The fix: drain the buffer under the lock (fast), release the lock, then write to the database outside the lock.

## Actions

1. Read `services/shared/audit.py` in full.

2. Find the flush method (likely `_flush()` or `flush()`). The current pattern is approximately:
   ```python
   async with self._lock:
       events = []
       while self.buffer:
           events.append(self.buffer.popleft())
       async with self.pool.acquire() as conn:
           await conn.copy_records_to_table(...)  # ← I/O inside lock
   ```

3. Restructure it to:
   ```python
   # Step 1: drain buffer under lock (fast, in-memory only)
   async with self._lock:
       events = list(self.buffer)
       self.buffer.clear()

   # Step 2: write to database OUTSIDE the lock
   if events:
       try:
           async with self.pool.acquire() as conn:
               await conn.copy_records_to_table(...)
       except Exception:
           # On failure, put events back in the buffer for retry
           async with self._lock:
               self.buffer.extendleft(reversed(events))
           logger.warning("audit flush failed, events re-queued", exc_info=True)
   ```

4. Verify the re-queue logic doesn't cause unbounded growth: add a max buffer size check. If `len(self.buffer) > MAX_AUDIT_BUFFER` (e.g., 10,000), drop the oldest events with a warning log rather than continuing to grow.

5. Do not change the public API of `AuditLogger`.

## Verification

The flush method must not hold `self._lock` during any `await` call after this change.

```bash
# Manually read the file and verify the restructuring looks correct
grep -n 'async with self._lock' services/shared/audit.py
# Should show the lock used only for buffer drain, not for I/O
```
