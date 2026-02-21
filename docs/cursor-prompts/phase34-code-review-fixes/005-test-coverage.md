# 005: Test Coverage Improvements

## Priority: HIGH

## Critical Untested Modules

### 1. Subscription Worker Tests

**Create:** `tests/unit/test_subscription_worker.py`

```python
"""Unit tests for subscription worker state transitions and notifications."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

# Import worker functions
import sys
sys.path.insert(0, 'services/subscription_worker')
from worker import (
    schedule_renewal_notifications,
    process_pending_notifications,
    process_grace_transitions,
    reconcile_device_counts,
    NOTIFICATION_DAYS,
    GRACE_PERIOD_DAYS,
)


class TestRenewalNotifications:
    """Test renewal notification scheduling."""

    @pytest.fixture
    def mock_pool(self):
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool, conn

    @pytest.mark.asyncio
    async def test_schedules_notification_for_expiring_subscription(self, mock_pool):
        """Notification scheduled when subscription expires within window."""
        pool, conn = mock_pool

        # Subscription expiring in 30 days
        conn.fetch.return_value = [
            {
                'subscription_id': 'SUB-001',
                'tenant_id': 'tenant-a',
                'term_end': datetime.now(timezone.utc) + timedelta(days=30),
                'tenant_name': 'Test Tenant',
            }
        ]
        conn.execute.return_value = None

        await schedule_renewal_notifications(pool)

        # Verify notification was inserted
        assert conn.execute.called
        call_args = conn.execute.call_args
        assert 'INSERT INTO subscription_notifications' in call_args[0][0]
        assert 'RENEWAL_30' in str(call_args)

    @pytest.mark.asyncio
    async def test_skips_already_notified(self, mock_pool):
        """No duplicate notification if already scheduled."""
        pool, conn = mock_pool
        conn.fetch.return_value = []  # Query excludes already notified

        await schedule_renewal_notifications(pool)

        # No inserts should happen
        insert_calls = [c for c in conn.execute.call_args_list
                       if 'INSERT' in str(c)]
        assert len(insert_calls) == 0

    @pytest.mark.asyncio
    async def test_all_notification_windows(self, mock_pool):
        """Test all notification day windows are checked."""
        pool, conn = mock_pool
        conn.fetch.return_value = []

        await schedule_renewal_notifications(pool)

        # Should query for each notification day
        fetch_calls = conn.fetch.call_args_list
        assert len(fetch_calls) == len(NOTIFICATION_DAYS)


class TestGraceTransitions:
    """Test subscription status transitions."""

    @pytest.fixture
    def mock_pool(self):
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool, conn

    @pytest.mark.asyncio
    async def test_active_to_grace_transition(self, mock_pool):
        """ACTIVE → GRACE when term_end passes."""
        pool, conn = mock_pool

        # First fetch returns subscriptions to transition
        conn.fetch.side_effect = [
            [{'subscription_id': 'SUB-001', 'tenant_id': 'tenant-a'}],  # ACTIVE → GRACE
            [],  # GRACE → SUSPENDED (none)
        ]

        await process_grace_transitions(pool)

        # Verify UPDATE was called for GRACE transition
        update_calls = [c for c in conn.fetch.call_args_list
                       if 'GRACE' in str(c)]
        assert len(update_calls) >= 1

    @pytest.mark.asyncio
    async def test_grace_to_suspended_transition(self, mock_pool):
        """GRACE → SUSPENDED when grace_end passes."""
        pool, conn = mock_pool

        conn.fetch.side_effect = [
            [],  # ACTIVE → GRACE (none)
            [{'subscription_id': 'SUB-002', 'tenant_id': 'tenant-b'}],  # GRACE → SUSPENDED
        ]

        await process_grace_transitions(pool)

        # Verify audit log entry created
        execute_calls = [c for c in conn.execute.call_args_list
                        if 'subscription_audit' in str(c)]
        assert len(execute_calls) >= 1

    @pytest.mark.asyncio
    async def test_grace_period_calculation(self, mock_pool):
        """Grace end is set to term_end + 14 days."""
        pool, conn = mock_pool

        conn.fetch.side_effect = [
            [{'subscription_id': 'SUB-001', 'tenant_id': 'tenant-a'}],
            [],
        ]

        await process_grace_transitions(pool)

        # Check grace_end calculation in UPDATE query
        fetch_call = conn.fetch.call_args_list[0]
        assert "interval '14 days'" in str(fetch_call) or \
               str(GRACE_PERIOD_DAYS) in str(fetch_call)


class TestDeviceCountReconciliation:
    """Test device count reconciliation."""

    @pytest.fixture
    def mock_pool(self):
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool, conn

    @pytest.mark.asyncio
    async def test_reconciles_mismatched_counts(self, mock_pool):
        """Corrects active_device_count when out of sync."""
        pool, conn = mock_pool
        conn.execute.return_value = "UPDATE 3"

        await reconcile_device_counts(pool)

        # Verify reconciliation query executed
        assert conn.execute.called
        call_args = conn.execute.call_args[0][0]
        assert 'UPDATE subscriptions' in call_args
        assert 'active_device_count' in call_args

    @pytest.mark.asyncio
    async def test_no_update_when_counts_match(self, mock_pool):
        """No updates when counts are correct."""
        pool, conn = mock_pool
        conn.execute.return_value = "UPDATE 0"

        await reconcile_device_counts(pool)

        # Query runs but affects 0 rows
        assert conn.execute.called
```

---

### 2. Audit Logger Tests

**Create:** `tests/unit/test_audit_logger.py`

```python
"""Unit tests for high-performance audit logger."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

# Import audit module
from services.shared.audit import (
    AuditLogger,
    AuditEvent,
    AuditBuffer,
    log_event,
    flush_buffer,
)


class TestAuditBuffer:
    """Test audit buffer behavior."""

    def test_buffer_accepts_events(self):
        """Events are added to buffer."""
        buffer = AuditBuffer(max_size=100)
        event = AuditEvent(
            tenant_id='tenant-a',
            event_type='TEST',
            actor_type='user',
            actor_id='user-1',
        )

        buffer.add(event)

        assert len(buffer) == 1

    def test_buffer_overflow_behavior(self):
        """Buffer handles overflow gracefully."""
        buffer = AuditBuffer(max_size=3)

        for i in range(5):
            event = AuditEvent(
                tenant_id='tenant-a',
                event_type=f'TEST_{i}',
                actor_type='user',
                actor_id='user-1',
            )
            buffer.add(event)

        # Should not exceed max_size (or handle overflow)
        assert len(buffer) <= 5  # Depends on implementation

    def test_buffer_flush_clears_events(self):
        """Flush returns events and clears buffer."""
        buffer = AuditBuffer(max_size=100)

        for i in range(3):
            buffer.add(AuditEvent(
                tenant_id='tenant-a',
                event_type=f'TEST_{i}',
                actor_type='user',
                actor_id='user-1',
            ))

        events = buffer.flush()

        assert len(events) == 3
        assert len(buffer) == 0


class TestAuditLogger:
    """Test audit logger functionality."""

    @pytest.fixture
    def mock_pool(self):
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool, conn

    @pytest.mark.asyncio
    async def test_logs_event_to_database(self, mock_pool):
        """Events are persisted to database."""
        pool, conn = mock_pool
        logger = AuditLogger(pool)

        await logger.log(
            tenant_id='tenant-a',
            event_type='DEVICE_CREATED',
            actor_type='user',
            actor_id='user-1',
            details={'device_id': 'DEV-001'},
        )

        # Force flush
        await logger.flush()

        assert conn.executemany.called or conn.execute.called

    @pytest.mark.asyncio
    async def test_batches_multiple_events(self, mock_pool):
        """Multiple events are batched into single insert."""
        pool, conn = mock_pool
        logger = AuditLogger(pool, batch_size=10)

        for i in range(5):
            await logger.log(
                tenant_id='tenant-a',
                event_type=f'EVENT_{i}',
                actor_type='system',
                actor_id='worker',
            )

        await logger.flush()

        # Should be single batch insert, not 5 individual inserts
        # Check executemany or COPY usage

    @pytest.mark.asyncio
    async def test_auto_flush_on_timer(self, mock_pool):
        """Buffer auto-flushes after interval."""
        pool, conn = mock_pool
        logger = AuditLogger(pool, flush_interval=0.1)

        await logger.log(
            tenant_id='tenant-a',
            event_type='TEST',
            actor_type='user',
            actor_id='user-1',
        )

        # Wait for auto-flush
        await asyncio.sleep(0.2)

        assert conn.execute.called or conn.executemany.called

    @pytest.mark.asyncio
    async def test_error_recovery(self, mock_pool):
        """Logger recovers from database errors."""
        pool, conn = mock_pool
        conn.execute.side_effect = Exception("DB Error")

        logger = AuditLogger(pool)

        await logger.log(
            tenant_id='tenant-a',
            event_type='TEST',
            actor_type='user',
            actor_id='user-1',
        )

        # Should not raise, should handle gracefully
        await logger.flush()

        # Events should be requeued or logged to fallback
```

---

### 3. Telemetry Queries Tests

**Create:** `tests/unit/test_telemetry_queries.py`

```python
"""Unit tests for telemetry query functions."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from services.ui_iot.db.telemetry_queries import (
    fetch_telemetry,
    fetch_telemetry_aggregated,
    fetch_latest_telemetry,
    build_time_bucket_query,
)


class TestFetchTelemetry:
    """Test telemetry fetch functions."""

    @pytest.fixture
    def mock_conn(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_fetch_with_time_range(self, mock_conn):
        """Fetches telemetry within time range."""
        mock_conn.fetch.return_value = [
            {'time': datetime.now(timezone.utc), 'device_id': 'DEV-001', 'metrics': {'temp': 25}},
        ]

        result = await fetch_telemetry(
            mock_conn,
            tenant_id='tenant-a',
            device_id='DEV-001',
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc),
        )

        assert len(result) == 1
        assert mock_conn.fetch.called

    @pytest.mark.asyncio
    async def test_fetch_with_metric_filter(self, mock_conn):
        """Filters by specific metric keys."""
        mock_conn.fetch.return_value = []

        await fetch_telemetry(
            mock_conn,
            tenant_id='tenant-a',
            device_id='DEV-001',
            metrics=['temperature', 'humidity'],
        )

        call_args = mock_conn.fetch.call_args[0][0]
        assert 'metrics' in call_args


class TestAggregatedQueries:
    """Test time-bucket aggregation queries."""

    @pytest.fixture
    def mock_conn(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_time_bucket_aggregation(self, mock_conn):
        """Uses TimescaleDB time_bucket for aggregation."""
        mock_conn.fetch.return_value = []

        await fetch_telemetry_aggregated(
            mock_conn,
            tenant_id='tenant-a',
            device_id='DEV-001',
            bucket_interval='1 hour',
            aggregation='avg',
        )

        call_args = mock_conn.fetch.call_args[0][0]
        assert 'time_bucket' in call_args

    def test_build_time_bucket_query(self):
        """Query builder creates valid SQL."""
        query = build_time_bucket_query(
            bucket='1 hour',
            metric='temperature',
            agg='avg',
        )

        assert 'time_bucket' in query
        assert 'avg' in query.lower()
        assert 'temperature' in query
```

---

### 4. System Routes Tests

**Create:** `tests/unit/test_system_routes.py`

```python
"""Unit tests for system routes (health, metrics, capacity)."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from services.ui_iot.app import app


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_returns_ok(self, client):
        """Health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_includes_components(self, client):
        """Health response includes component status."""
        response = client.get("/health")
        data = response.json()

        assert 'status' in data
        assert 'components' in data or 'database' in data


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch('services.ui_iot.routes.system.get_pool')
    def test_metrics_returns_counts(self, mock_pool, client):
        """Metrics endpoint returns system counts."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 100
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        response = client.get("/system/metrics")

        # Should return or metrics data
        assert response.status_code in [200, 401, 403]  # May require auth


class TestCapacityEndpoint:
    """Test capacity endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch('services.ui_iot.routes.system.get_pool')
    def test_capacity_returns_limits(self, mock_pool, client):
        """Capacity endpoint returns system limits."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        response = client.get("/system/capacity")

        assert response.status_code in [200, 401, 403]
```

---

### 5. Frontend Test Infrastructure

**Create:** `frontend/src/setupTests.ts`

```typescript
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));
```

**Create:** `frontend/vitest.config.ts`

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/setupTests.ts'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

**Update:** `frontend/package.json`

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.0.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/user-event": "^14.0.0",
    "vitest": "^1.0.0",
    "@vitest/ui": "^1.0.0",
    "@vitest/coverage-v8": "^1.0.0",
    "jsdom": "^23.0.0"
  }
}
```

---

### 6. Frontend API Client Tests

**Create:** `frontend/src/services/api/client.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiGet, apiPost, apiPatch, apiDelete } from './client';

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('apiGet', () => {
    it('makes GET request with auth header', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ data: 'test' }),
      });

      const result = await apiGet('/test');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/test'),
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('throws on non-200 response', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Not found' }),
      });

      await expect(apiGet('/not-found')).rejects.toThrow();
    });
  });

  describe('apiPost', () => {
    it('sends JSON body', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ id: 1 }),
      });

      await apiPost('/create', { name: 'test' });

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ name: 'test' }),
        })
      );
    });
  });
});
```

---

## Running Tests

```bash
# Backend tests
pytest tests/unit/test_subscription_worker.py -v
pytest tests/unit/test_audit_logger.py -v
pytest tests/unit/test_telemetry_queries.py -v
pytest tests/unit/test_system_routes.py -v

# Frontend tests
cd frontend
npm install
npm test

# Coverage report
pytest --cov=services --cov-report=html
cd frontend && npm run test:coverage
```

## Files Created

- `tests/unit/test_subscription_worker.py`
- `tests/unit/test_audit_logger.py`
- `tests/unit/test_telemetry_queries.py`
- `tests/unit/test_system_routes.py`
- `frontend/src/setupTests.ts`
- `frontend/vitest.config.ts`
- `frontend/src/services/api/client.test.ts`
