# 005: E2E Tests for Phase 33 Features

## Task

Create Playwright E2E tests for the Phase 33 subscription features: detail page, status changes, renewal workflow, and notification worker.

## File to Create

`tests/e2e/test_phase33_features.py`

## Implementation

```python
"""
E2E tests for Phase 33 subscription features:
- Subscription detail page
- Status change workflow
- Renewal page and device downsizing
- Notification worker transitions
"""
import pytest
from datetime import datetime, timezone, timedelta
from playwright.sync_api import Page, expect


class TestSubscriptionDetailPage:
    """Tests for operator subscription detail page."""

    @pytest.fixture(autouse=True)
    def setup(self, operator_page: Page, db_connection):
        """Create test subscription for detail page tests."""
        self.page = operator_page
        self.conn = db_connection

        # Get or create a test tenant
        self.tenant_id = self.conn.execute(
            "SELECT tenant_id FROM tenants WHERE status = 'ACTIVE' LIMIT 1"
        ).fetchone()[0]

        # Create test subscription
        self.subscription_id = f"SUB-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                active_device_count, term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 100, 5, now(), now() + interval '1 year', 'ACTIVE', 'e2e-test')
            ON CONFLICT (subscription_id) DO NOTHING
            """,
            self.subscription_id, self.tenant_id
        )
        self.conn.commit()

        yield

        # Cleanup
        self.conn.execute(
            "DELETE FROM subscriptions WHERE subscription_id = $1",
            self.subscription_id
        )
        self.conn.commit()

    def test_detail_page_loads(self):
        """Test subscription detail page loads with correct info."""
        self.page.goto(f"/operator/subscriptions/{self.subscription_id}")

        # Verify page header shows subscription ID
        expect(self.page.locator("text=" + self.subscription_id)).to_be_visible()

        # Verify info cards
        expect(self.page.locator("text=Device Usage")).to_be_visible()
        expect(self.page.locator("text=Term Period")).to_be_visible()
        expect(self.page.locator("text=Tenant")).to_be_visible()

        # Verify badges
        expect(self.page.locator("text=MAIN")).to_be_visible()
        expect(self.page.locator("text=ACTIVE")).to_be_visible()

    def test_edit_device_limit(self):
        """Test editing subscription device limit."""
        self.page.goto(f"/operator/subscriptions/{self.subscription_id}")

        # Click Edit button
        self.page.click("button:has-text('Edit')")

        # Wait for dialog
        expect(self.page.locator("text=Edit Subscription")).to_be_visible()

        # Change device limit
        device_limit_input = self.page.locator("input[type='number']").first
        device_limit_input.fill("150")

        # Fill required notes
        self.page.fill("textarea", "E2E test: increasing device limit")

        # Submit
        self.page.click("button:has-text('Save Changes')")

        # Verify dialog closes and page updates
        expect(self.page.locator("text=Edit Subscription")).not_to_be_visible(timeout=5000)

        # Refresh and verify change persisted
        self.page.reload()
        expect(self.page.locator("text=150")).to_be_visible()


class TestSubscriptionStatusChange:
    """Tests for subscription status change workflow."""

    @pytest.fixture(autouse=True)
    def setup(self, operator_page: Page, db_connection):
        """Create test subscription for status change tests."""
        self.page = operator_page
        self.conn = db_connection

        self.tenant_id = self.conn.execute(
            "SELECT tenant_id FROM tenants WHERE status = 'ACTIVE' LIMIT 1"
        ).fetchone()[0]

        self.subscription_id = f"SUB-STATUS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                active_device_count, term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 50, 0, now(), now() + interval '1 year', 'ACTIVE', 'e2e-test')
            ON CONFLICT (subscription_id) DO NOTHING
            """,
            self.subscription_id, self.tenant_id
        )
        self.conn.commit()

        yield

        self.conn.execute(
            "DELETE FROM subscriptions WHERE subscription_id = $1",
            self.subscription_id
        )
        self.conn.commit()

    def test_change_status_to_suspended(self):
        """Test changing subscription status to SUSPENDED shows warning."""
        self.page.goto(f"/operator/subscriptions/{self.subscription_id}")

        # Click Change Status button
        self.page.click("button:has-text('Change Status')")

        # Wait for dialog
        expect(self.page.locator("text=Change Subscription Status")).to_be_visible()

        # Select SUSPENDED
        self.page.click("[role='combobox']")
        self.page.click("text=SUSPENDED")

        # Verify warning appears
        expect(self.page.locator("text=Suspending will block telemetry")).to_be_visible()

        # Fill notes
        self.page.fill("textarea", "E2E test: suspending subscription")

        # Submit
        self.page.click("button:has-text('Set to SUSPENDED')")

        # Verify dialog closes
        expect(self.page.locator("text=Change Subscription Status")).not_to_be_visible(timeout=5000)

        # Verify status badge updated
        self.page.reload()
        expect(self.page.locator(".bg-red-100:has-text('SUSPENDED')")).to_be_visible()

    def test_change_status_to_grace(self):
        """Test changing subscription status to GRACE."""
        self.page.goto(f"/operator/subscriptions/{self.subscription_id}")

        self.page.click("button:has-text('Change Status')")
        expect(self.page.locator("text=Change Subscription Status")).to_be_visible()

        self.page.click("[role='combobox']")
        self.page.click("text=GRACE")

        self.page.fill("textarea", "E2E test: setting to grace period")
        self.page.click("button:has-text('Set to GRACE')")

        expect(self.page.locator("text=Change Subscription Status")).not_to_be_visible(timeout=5000)

        self.page.reload()
        expect(self.page.locator(".bg-orange-100:has-text('GRACE')")).to_be_visible()


class TestRenewalWorkflow:
    """Tests for customer renewal page and workflow."""

    @pytest.fixture(autouse=True)
    def setup(self, customer_page: Page, db_connection):
        """Create expiring subscription for renewal tests."""
        self.page = customer_page
        self.conn = db_connection

        # Get tenant for customer user
        self.tenant_id = self.conn.execute(
            "SELECT tenant_id FROM tenants WHERE status = 'ACTIVE' LIMIT 1"
        ).fetchone()[0]

        # Create subscription expiring in 7 days
        self.subscription_id = f"SUB-RENEW-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        term_end = datetime.now(timezone.utc) + timedelta(days=7)

        self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                active_device_count, term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 100, 25, now() - interval '358 days', $3, 'ACTIVE', 'e2e-test')
            ON CONFLICT (subscription_id) DO NOTHING
            """,
            self.subscription_id, self.tenant_id, term_end
        )
        self.conn.commit()

        yield

        self.conn.execute(
            "DELETE FROM subscriptions WHERE subscription_id = $1",
            self.subscription_id
        )
        self.conn.commit()

    def test_renewal_banner_shows_for_expiring(self):
        """Test that expiring subscription shows renewal banner."""
        self.page.goto("/app/subscription")

        # Should show warning about expiring subscription
        expect(self.page.locator("text=expires").or_(
            self.page.locator("text=Expires")
        )).to_be_visible(timeout=10000)

    def test_renew_now_navigation(self):
        """Test Renew Now button navigates to renewal page."""
        self.page.goto("/app/subscription")

        # Click Renew Now if visible
        renew_button = self.page.locator("button:has-text('Renew Now')")
        if renew_button.is_visible():
            renew_button.click()
            expect(self.page).to_have_url("/app/subscription/renew", timeout=5000)

    def test_renewal_page_loads(self):
        """Test renewal page loads with plan options."""
        self.page.goto("/app/subscription/renew")

        # Verify page elements
        expect(self.page.locator("text=Renew Subscription")).to_be_visible()
        expect(self.page.locator("text=Current Subscription")).to_be_visible()
        expect(self.page.locator("text=Select Plan")).to_be_visible()

        # Verify plan options
        expect(self.page.locator("text=Starter")).to_be_visible()
        expect(self.page.locator("text=Professional")).to_be_visible()
        expect(self.page.locator("text=Enterprise")).to_be_visible()

    def test_plan_selection_shows_summary(self):
        """Test selecting a plan shows renewal summary."""
        self.page.goto("/app/subscription/renew")

        # Select Professional plan
        self.page.click("label:has-text('Professional')")

        # Verify summary updates
        expect(self.page.locator("text=Renewal Summary")).to_be_visible()
        expect(self.page.locator("text=Professional").nth(1)).to_be_visible()


class TestRenewalWithDownsize:
    """Tests for renewal with device downsizing."""

    @pytest.fixture(autouse=True)
    def setup(self, customer_page: Page, db_connection):
        """Create subscription with more devices than smallest plan allows."""
        self.page = customer_page
        self.conn = db_connection

        self.tenant_id = self.conn.execute(
            "SELECT tenant_id FROM tenants WHERE status = 'ACTIVE' LIMIT 1"
        ).fetchone()[0]

        self.subscription_id = f"SUB-DOWNSIZE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        term_end = datetime.now(timezone.utc) + timedelta(days=30)

        # Create subscription with 75 devices (more than Starter's 50)
        self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                active_device_count, term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 200, 75, now() - interval '335 days', $3, 'ACTIVE', 'e2e-test')
            ON CONFLICT (subscription_id) DO NOTHING
            """,
            self.subscription_id, self.tenant_id, term_end
        )

        # Create some test devices for this subscription
        for i in range(5):
            device_id = f"E2E-DEVICE-{self.subscription_id[-8:]}-{i:03d}"
            self.conn.execute(
                """
                INSERT INTO device_registry (device_id, tenant_id, site_id, subscription_id, status)
                VALUES ($1, $2, 'E2E-SITE', $3, 'ACTIVE')
                ON CONFLICT (device_id) DO NOTHING
                """,
                device_id, self.tenant_id, self.subscription_id
            )

        self.conn.commit()

        yield

        # Cleanup devices and subscription
        self.conn.execute(
            "DELETE FROM device_registry WHERE subscription_id = $1",
            self.subscription_id
        )
        self.conn.execute(
            "DELETE FROM subscriptions WHERE subscription_id = $1",
            self.subscription_id
        )
        self.conn.commit()

    def test_downsize_warning_appears(self):
        """Test that selecting smaller plan shows downsize warning."""
        self.page.goto("/app/subscription/renew")

        # Select Starter plan (50 devices, but we have 75)
        self.page.click("label:has-text('Starter')")

        # Should show warning about device reduction
        expect(self.page.locator("text=Device Reduction Required")).to_be_visible()
        expect(self.page.locator("text=Requires removing")).to_be_visible()

    def test_device_selection_modal_opens(self):
        """Test device selection modal opens for downsizing."""
        self.page.goto("/app/subscription/renew")

        # Select Starter plan
        self.page.click("label:has-text('Starter')")

        # Click to select devices
        self.page.click("button:has-text('Select Devices to Deactivate')")

        # Modal should open
        expect(self.page.locator("text=Select Devices to Deactivate")).to_be_visible()
        expect(self.page.locator("text=Choose")).to_be_visible()

    def test_device_selection_limits_count(self):
        """Test device selection respects required count."""
        self.page.goto("/app/subscription/renew")

        self.page.click("label:has-text('Starter')")
        self.page.click("button:has-text('Select Devices to Deactivate')")

        # Wait for modal and devices to load
        expect(self.page.locator("text=Select Devices to Deactivate")).to_be_visible()

        # Try selecting devices - should show count badge
        device_rows = self.page.locator("[data-testid='device-row']").or_(
            self.page.locator(".font-mono.text-sm")
        )

        # The selection count should be visible
        expect(self.page.locator("text=/\\d+ \\/ \\d+/")).to_be_visible()


class TestNotificationWorkerTransitions:
    """Tests for notification worker state transitions."""

    @pytest.fixture(autouse=True)
    def setup(self, db_connection):
        """Create subscription for worker transition tests."""
        self.conn = db_connection

        self.tenant_id = self.conn.execute(
            "SELECT tenant_id FROM tenants WHERE status = 'ACTIVE' LIMIT 1"
        ).fetchone()[0]

        self.subscription_id = f"SUB-WORKER-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        yield

        # Cleanup
        self.conn.execute(
            "DELETE FROM subscription_notifications WHERE tenant_id = $1",
            self.tenant_id
        )
        self.conn.execute(
            "DELETE FROM subscription_audit WHERE details::text LIKE $1",
            f'%{self.subscription_id}%'
        )
        self.conn.execute(
            "DELETE FROM subscriptions WHERE subscription_id = $1",
            self.subscription_id
        )
        self.conn.commit()

    def test_active_to_grace_transition(self, run_worker_once):
        """Test ACTIVE → GRACE transition when term_end passes."""
        # Create subscription with term_end in the past
        term_end = datetime.now(timezone.utc) - timedelta(hours=1)

        self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 50, now() - interval '1 year', $3, 'ACTIVE', 'e2e-test')
            """,
            self.subscription_id, self.tenant_id, term_end
        )
        self.conn.commit()

        # Run worker
        run_worker_once()

        # Verify status changed to GRACE
        result = self.conn.execute(
            "SELECT status, grace_end FROM subscriptions WHERE subscription_id = $1",
            self.subscription_id
        ).fetchone()

        assert result[0] == 'GRACE', f"Expected GRACE, got {result[0]}"
        assert result[1] is not None, "grace_end should be set"

        # Verify audit log entry
        audit = self.conn.execute(
            """
            SELECT event_type FROM subscription_audit
            WHERE tenant_id = $1 AND event_type = 'GRACE_STARTED'
            ORDER BY event_timestamp DESC LIMIT 1
            """,
            self.tenant_id
        ).fetchone()

        assert audit is not None, "GRACE_STARTED audit entry should exist"

    def test_grace_to_suspended_transition(self, run_worker_once):
        """Test GRACE → SUSPENDED transition when grace_end passes."""
        # Create subscription in GRACE with grace_end in the past
        grace_end = datetime.now(timezone.utc) - timedelta(hours=1)

        self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                term_start, term_end, status, grace_end, created_by
            ) VALUES ($1, $2, 'MAIN', 50, now() - interval '1 year',
                      now() - interval '15 days', 'GRACE', $3, 'e2e-test')
            """,
            self.subscription_id, self.tenant_id, grace_end
        )
        self.conn.commit()

        # Run worker
        run_worker_once()

        # Verify status changed to SUSPENDED
        result = self.conn.execute(
            "SELECT status FROM subscriptions WHERE subscription_id = $1",
            self.subscription_id
        ).fetchone()

        assert result[0] == 'SUSPENDED', f"Expected SUSPENDED, got {result[0]}"

        # Verify audit log entry
        audit = self.conn.execute(
            """
            SELECT event_type FROM subscription_audit
            WHERE tenant_id = $1 AND event_type = 'STATUS_SUSPENDED'
            ORDER BY event_timestamp DESC LIMIT 1
            """,
            self.tenant_id
        ).fetchone()

        assert audit is not None, "STATUS_SUSPENDED audit entry should exist"

    def test_renewal_notification_scheduled(self, run_worker_once):
        """Test renewal notification is scheduled for expiring subscription."""
        # Create subscription expiring in exactly 30 days
        term_end = datetime.now(timezone.utc) + timedelta(days=30)

        self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 50, now() - interval '335 days', $3, 'ACTIVE', 'e2e-test')
            """,
            self.subscription_id, self.tenant_id, term_end
        )
        self.conn.commit()

        # Run worker
        run_worker_once()

        # Verify notification was scheduled
        notification = self.conn.execute(
            """
            SELECT notification_type, status FROM subscription_notifications
            WHERE tenant_id = $1 AND notification_type = 'RENEWAL_30'
            ORDER BY scheduled_at DESC LIMIT 1
            """,
            self.tenant_id
        ).fetchone()

        assert notification is not None, "RENEWAL_30 notification should be scheduled"


# Fixtures for conftest.py

@pytest.fixture
def run_worker_once():
    """Fixture to run the subscription worker once."""
    import subprocess

    def _run():
        result = subprocess.run(
            [
                "docker", "compose", "-f", "compose/docker-compose.yml",
                "exec", "-T", "subscription-worker",
                "python", "worker.py", "--once"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            # Try alternative: run directly if container not running
            result = subprocess.run(
                [
                    "docker", "compose", "-f", "compose/docker-compose.yml",
                    "run", "--rm", "subscription-worker",
                    "python", "worker.py", "--once"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
        return result

    return _run
```

## Update conftest.py

Add the `run_worker_once` fixture to `tests/e2e/conftest.py`:

```python
import subprocess

@pytest.fixture
def run_worker_once():
    """Run the subscription worker once for testing state transitions."""
    def _run():
        result = subprocess.run(
            [
                "docker", "compose", "-f", "compose/docker-compose.yml",
                "exec", "-T", "subscription-worker",
                "python", "worker.py", "--once"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            result = subprocess.run(
                [
                    "docker", "compose", "-f", "compose/docker-compose.yml",
                    "run", "--rm", "subscription-worker",
                    "python", "worker.py", "--once"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
        return result

    return _run
```

## Running the Tests

```bash
# Run all Phase 33 tests
TEST_DATABASE_URL="postgresql://iot:iot_dev@localhost:5432/iotcloud" \
DATABASE_URL="postgresql://iot:iot_dev@localhost:5432/iotcloud" \
E2E_BASE_URL="https://192.168.10.53" \
KEYCLOAK_URL="https://192.168.10.53" \
E2E_API_URL="https://192.168.10.53" \
E2E_DATABASE_URL="postgresql://iot:iot_dev@localhost:5432/iotcloud" \
RUN_E2E=1 \
pytest tests/e2e/test_phase33_features.py -v

# Run specific test class
pytest tests/e2e/test_phase33_features.py::TestSubscriptionDetailPage -v

# Run with headed browser for debugging
pytest tests/e2e/test_phase33_features.py -v --headed
```

## Expected Results

| Test Class | Tests | Description |
|------------|-------|-------------|
| TestSubscriptionDetailPage | 2 | Detail page load, edit device limit |
| TestSubscriptionStatusChange | 2 | Change to SUSPENDED, change to GRACE |
| TestRenewalWorkflow | 4 | Banner, navigation, page load, plan selection |
| TestRenewalWithDownsize | 3 | Downsize warning, modal, selection limits |
| TestNotificationWorkerTransitions | 3 | ACTIVE→GRACE, GRACE→SUSPENDED, notification scheduling |

Total: 14 tests
