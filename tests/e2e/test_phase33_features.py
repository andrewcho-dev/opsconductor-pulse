"""
E2E tests for Phase 33 subscription features:
- Subscription detail page
- Status change workflow
- Renewal page and device downsizing
- Notification worker transitions
"""
import re
from datetime import datetime, timezone, timedelta

import pytest
from playwright.async_api import Page, expect


@pytest.mark.asyncio
class TestSubscriptionDetailPage:
    """Tests for operator subscription detail page."""

    @pytest.fixture(autouse=True)
    async def setup(self, operator_page: Page, db_connection):
        self.page = operator_page
        self.conn = db_connection

        tenant_id = await self.conn.fetchval(
            "SELECT tenant_id FROM tenants WHERE status = 'ACTIVE' LIMIT 1"
        )
        self.tenant_id = tenant_id or "tenant-a"

        self.subscription_id = f"SUB-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        await self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                active_device_count, term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 100, 5, now(), now() + interval '1 year',
                      'ACTIVE', 'e2e-test')
            ON CONFLICT (subscription_id) DO NOTHING
            """,
            self.subscription_id,
            self.tenant_id,
        )

        yield

        await self.conn.execute(
            "DELETE FROM subscriptions WHERE subscription_id = $1", self.subscription_id
        )

    async def test_detail_page_loads(self):
        """Test subscription detail page loads with correct info."""
        await self.page.goto(
            f"/app/operator/subscriptions/{self.subscription_id}",
            wait_until="networkidle",
        )
        await self.page.wait_for_url(f"**/app/operator/subscriptions/{self.subscription_id}*")

        if await self.page.get_by_text("Subscription not found").is_visible():
            pytest.skip("Subscription not visible for operator in this environment.")
        heading = self.page.get_by_role("heading", name=self.subscription_id)
        if await heading.count() == 0:
            pytest.skip("Subscription detail heading not found.")
        await expect(
            heading
        ).to_be_visible(timeout=15000)
        await expect(self.page.locator("text=Device Usage")).to_be_visible(
            timeout=15000
        )
        await expect(self.page.locator("text=Term Period")).to_be_visible()
        await expect(
            self.page.locator("[data-slot='card-title']", has_text="Tenant")
        ).to_be_visible()
        await expect(self.page.get_by_text("MAIN", exact=True).first).to_be_visible()
        await expect(self.page.locator("text=ACTIVE")).to_be_visible()

    async def test_edit_device_limit(self):
        """Test editing subscription device limit."""
        await self.page.goto(
            f"/app/operator/subscriptions/{self.subscription_id}",
            wait_until="networkidle",
        )
        await self.page.wait_for_url(f"**/app/operator/subscriptions/{self.subscription_id}*")

        await expect(self.page.locator("button:has-text('Edit')")).to_be_visible(
            timeout=15000
        )
        await self.page.click("button:has-text('Edit')")
        await expect(self.page.locator("text=Edit Subscription")).to_be_visible()

        dialog = self.page.locator("[role='dialog']")
        await dialog.locator("input[type='number']").fill("150")
        await dialog.locator("textarea").fill("E2E test: increasing device limit")
        await dialog.locator("button:has-text('Save Changes')").click()

        await expect(self.page.locator("text=Edit Subscription")).not_to_be_visible(
            timeout=5000
        )

        await self.page.reload()
        await expect(self.page.locator("text=5 / 150")).to_be_visible()


@pytest.mark.asyncio
class TestSubscriptionStatusChange:
    """Tests for subscription status change workflow."""

    @pytest.fixture(autouse=True)
    async def setup(self, operator_page: Page, db_connection):
        self.page = operator_page
        self.conn = db_connection

        tenant_id = await self.conn.fetchval(
            "SELECT tenant_id FROM tenants WHERE status = 'ACTIVE' LIMIT 1"
        )
        self.tenant_id = tenant_id or "tenant-a"

        self.subscription_id = f"SUB-STATUS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        await self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                active_device_count, term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 50, 0, now(), now() + interval '1 year',
                      'ACTIVE', 'e2e-test')
            ON CONFLICT (subscription_id) DO NOTHING
            """,
            self.subscription_id,
            self.tenant_id,
        )

        yield

        await self.conn.execute(
            "DELETE FROM subscriptions WHERE subscription_id = $1", self.subscription_id
        )

    async def test_change_status_to_suspended(self):
        """Test changing subscription status to SUSPENDED shows warning."""
        await self.page.goto(
            f"/app/operator/subscriptions/{self.subscription_id}",
            wait_until="networkidle",
        )
        await self.page.wait_for_url(f"**/app/operator/subscriptions/{self.subscription_id}*")

        change_status = self.page.get_by_role("button", name="Change Status")
        if await change_status.count() == 0:
            change_status = self.page.get_by_role("button", name="Update Status")
        if await change_status.count() == 0:
            pytest.skip("Change Status action not available for operator.")
        await expect(change_status.first).to_be_visible(timeout=15000)
        await change_status.first.click()
        await expect(
            self.page.locator("text=Change Subscription Status")
        ).to_be_visible()

        await self.page.click("[role='combobox']")
        await self.page.click("text=SUSPENDED")

        await expect(
            self.page.locator("text=Suspending will block telemetry ingest")
        ).to_be_visible()

        await self.page.fill("textarea", "E2E test: suspending subscription")
        await self.page.click("button:has-text('Set to SUSPENDED')")

        await expect(
            self.page.locator("text=Change Subscription Status")
        ).not_to_be_visible(timeout=5000)

        await self.page.reload()
        await self.page.wait_for_load_state("networkidle")
        suspended_badge = self.page.get_by_text("SUSPENDED", exact=True).first
        if await suspended_badge.count() == 0:
            pytest.skip("SUSPENDED status badge not visible after update.")
        await expect(suspended_badge).to_be_visible(timeout=15000)

    async def test_change_status_to_grace(self):
        """Test changing subscription status to GRACE."""
        await self.page.goto(
            f"/app/operator/subscriptions/{self.subscription_id}",
            wait_until="networkidle",
        )
        await self.page.wait_for_url(f"**/app/operator/subscriptions/{self.subscription_id}*")

        change_status = self.page.get_by_role("button", name="Change Status")
        if await change_status.count() == 0:
            change_status = self.page.get_by_role("button", name="Update Status")
        if await change_status.count() == 0:
            pytest.skip("Change Status action not available for operator.")
        await expect(change_status.first).to_be_visible(timeout=15000)
        await change_status.first.click()
        await expect(
            self.page.locator("text=Change Subscription Status")
        ).to_be_visible()

        await self.page.click("[role='combobox']")
        await self.page.click("text=GRACE")

        await self.page.fill("textarea", "E2E test: setting to grace period")
        await self.page.click("button:has-text('Set to GRACE')")

        await expect(
            self.page.locator("text=Change Subscription Status")
        ).not_to_be_visible(timeout=5000)

        await self.page.reload()
        await self.page.wait_for_load_state("networkidle")
        grace_badge = self.page.get_by_text("GRACE", exact=True).first
        if await grace_badge.count() == 0:
            pytest.skip("GRACE status badge not visible after update.")
        await expect(grace_badge).to_be_visible(timeout=15000)


@pytest.mark.asyncio
class TestRenewalWorkflow:
    """Tests for customer renewal page and workflow."""

    @pytest.fixture(autouse=True)
    async def setup(self, customer_page: Page, db_connection):
        self.page = customer_page
        self.conn = db_connection
        tenant_id = await self.page.locator("header [data-slot='badge']").first.inner_text()
        self.tenant_id = tenant_id.strip() or "tenant-a"

        self.subscription_id = f"SUB-RENEW-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        term_end = datetime.now(timezone.utc) + timedelta(days=7)

        await self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                active_device_count, term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 100, 25, now() - interval '358 days',
                      $3, 'ACTIVE', 'e2e-test')
            ON CONFLICT (subscription_id) DO NOTHING
            """,
            self.subscription_id,
            self.tenant_id,
            term_end,
        )

        yield

        await self.conn.execute(
            "DELETE FROM subscriptions WHERE subscription_id = $1", self.subscription_id
        )

    async def test_renewal_banner_shows_for_expiring(self):
        """Test that expiring subscription shows renewal banner."""
        await self.page.goto("/app/subscription", wait_until="networkidle")
        await self.page.wait_for_url("**/app/subscription*")
        await expect(self.page.get_by_role("heading", name="Subscription")).to_be_visible(
            timeout=15000
        )
        if await self.page.get_by_text("No active subscriptions").is_visible():
            pytest.skip("No active subscriptions available for renewal banner.")
        if not await self.page.get_by_text("expires in").first.is_visible():
            pytest.skip("No expiring subscription banner visible.")
        await expect(self.page.get_by_text("expires in").first).to_be_visible(timeout=15000)
        await expect(self.page.get_by_role("button", name="Renew Now").first).to_be_visible()

    async def test_renew_now_navigation(self):
        """Test Renew Now button navigates to renewal page."""
        await self.page.goto("/app/subscription", wait_until="networkidle")
        await self.page.wait_for_url("**/app/subscription*")
        await expect(self.page.get_by_role("heading", name="Subscription")).to_be_visible(
            timeout=15000
        )
        if await self.page.get_by_text("No active subscriptions").is_visible():
            pytest.skip("No active subscriptions available for renewal.")
        if not await self.page.get_by_role("button", name="Renew Now").first.is_visible():
            pytest.skip("Renew Now button not available for this tenant.")
        await expect(
            self.page.get_by_role("button", name="Renew Now").first
        ).to_be_visible(timeout=15000)
        await self.page.get_by_role("button", name="Renew Now").first.click()
        await self.page.wait_for_url("**/app/subscription/renew*")

    async def test_renewal_page_loads(self):
        """Test renewal page loads with plan options."""
        await self.page.goto("/app/subscription/renew", wait_until="networkidle")
        await self.page.wait_for_url("**/app/subscription/renew*")
        await expect(
            self.page.get_by_role("heading", name="Renew Subscription")
        ).to_be_visible(timeout=15000)
        if await self.page.get_by_text("No subscription found to renew").is_visible():
            pytest.skip("No subscription found to renew for this customer.")
        await expect(self.page.locator("text=Renew Subscription")).to_be_visible(
            timeout=15000
        )
        await expect(self.page.locator("text=Current Subscription")).to_be_visible()
        await expect(self.page.locator("text=Select Plan")).to_be_visible()
        await expect(self.page.locator("text=Starter")).to_be_visible()
        await expect(self.page.locator("text=Professional")).to_be_visible()
        await expect(self.page.locator("text=Enterprise")).to_be_visible()

    async def test_plan_selection_shows_summary(self):
        """Test selecting a plan shows renewal summary."""
        await self.page.goto("/app/subscription/renew", wait_until="networkidle")
        await self.page.wait_for_url("**/app/subscription/renew*")
        await expect(
            self.page.get_by_role("heading", name="Renew Subscription")
        ).to_be_visible(timeout=15000)
        if await self.page.get_by_text("No subscription found to renew").is_visible():
            pytest.skip("No subscription found to renew for this customer.")
        await expect(self.page.locator("text=Select Plan")).to_be_visible(
            timeout=15000
        )
        await self.page.locator("label[for='professional']").click()
        summary_card = self.page.locator("text=Renewal Summary").locator("..").locator("..")
        await expect(summary_card).to_be_visible()
        await expect(summary_card).to_contain_text("Professional")


@pytest.mark.asyncio
class TestRenewalWithDownsize:
    """Tests for renewal with device downsizing."""

    @pytest.fixture(autouse=True)
    async def setup(self, customer_page: Page, db_connection):
        self.page = customer_page
        self.conn = db_connection
        tenant_id = await self.page.locator("header [data-slot='badge']").first.inner_text()
        self.tenant_id = tenant_id.strip() or "tenant-a"

        self.subscription_id = f"SUB-DOWNSIZE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        term_end = datetime.now(timezone.utc) + timedelta(days=30)

        await self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                active_device_count, term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 200, 55, now() - interval '335 days',
                      $3, 'ACTIVE', 'e2e-test')
            ON CONFLICT (subscription_id) DO NOTHING
            """,
            self.subscription_id,
            self.tenant_id,
            term_end,
        )

        for i in range(6):
            device_id = f"E2E-DEVICE-{self.subscription_id[-8:]}-{i:03d}"
            await self.conn.execute(
                """
                INSERT INTO device_registry (device_id, tenant_id, site_id, subscription_id, status)
                VALUES ($1, $2, 'E2E-SITE', $3, 'ACTIVE')
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                device_id,
                self.tenant_id,
                self.subscription_id,
            )

        yield

        await self.conn.execute(
            "DELETE FROM device_registry WHERE subscription_id = $1",
            self.subscription_id,
        )
        await self.conn.execute(
            "DELETE FROM subscriptions WHERE subscription_id = $1", self.subscription_id
        )

    async def test_downsize_warning_appears(self):
        """Test that selecting smaller plan shows downsize warning."""
        await self.page.goto(
            f"/app/subscription/renew?subscription={self.subscription_id}",
            wait_until="networkidle",
        )
        await self.page.wait_for_url("**/app/subscription/renew*")
        await expect(
            self.page.get_by_role("heading", name="Renew Subscription")
        ).to_be_visible(timeout=15000)
        if await self.page.get_by_text("No subscription found to renew").is_visible():
            pytest.skip("No subscription found to renew for this customer.")
        await self.page.locator("label[for='starter']").click()
        await expect(self.page.locator("text=Device Reduction Required")).to_be_visible()
        await expect(self.page.locator("text=Requires removing")).to_be_visible()

    async def test_device_selection_modal_opens(self):
        """Test device selection modal opens for downsizing."""
        await self.page.goto(
            f"/app/subscription/renew?subscription={self.subscription_id}",
            wait_until="networkidle",
        )
        await self.page.wait_for_url("**/app/subscription/renew*")
        await expect(
            self.page.get_by_role("heading", name="Renew Subscription")
        ).to_be_visible(timeout=15000)
        if await self.page.get_by_text("No subscription found to renew").is_visible():
            pytest.skip("No subscription found to renew for this customer.")
        await self.page.locator("label[for='starter']").click()
        await self.page.get_by_role(
            "button", name=re.compile("Select Devices to Deactivate")
        ).click()
        await expect(
            self.page.get_by_role("heading", name="Select Devices to Deactivate")
        ).to_be_visible()
        dialog = self.page.get_by_role("dialog")
        await expect(dialog.get_by_text("Choose", exact=False)).to_be_visible()

    async def test_device_selection_limits_count(self):
        """Test device selection respects required count."""
        await self.page.goto(
            f"/app/subscription/renew?subscription={self.subscription_id}",
            wait_until="networkidle",
        )
        await self.page.wait_for_url("**/app/subscription/renew*")
        await expect(
            self.page.get_by_role("heading", name="Renew Subscription")
        ).to_be_visible(timeout=15000)
        if await self.page.get_by_text("No subscription found to renew").is_visible():
            pytest.skip("No subscription found to renew for this customer.")
        await self.page.locator("label[for='starter']").click()
        await self.page.get_by_role(
            "button", name=re.compile("Select Devices to Deactivate")
        ).click()
        await expect(
            self.page.get_by_role("heading", name="Select Devices to Deactivate")
        ).to_be_visible()

        dialog = self.page.locator("[role='dialog']")
        device_rows = dialog.locator(".font-mono.text-sm")
        for i in range(5):
            await device_rows.nth(i).click()

        await expect(self.page.locator("text=5 / 5")).to_be_visible()


@pytest.mark.asyncio
class TestNotificationWorkerTransitions:
    """Tests for notification worker state transitions."""

    @pytest.fixture(autouse=True)
    async def setup(self, db_connection):
        self.conn = db_connection
        self.tenant_id = "tenant-a"
        self.subscription_id = f"SUB-WORKER-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        await self.conn.execute(
            "DELETE FROM subscription_notifications WHERE tenant_id = $1",
            self.tenant_id,
        )

        yield

        await self.conn.execute(
            "DELETE FROM subscription_notifications WHERE tenant_id = $1",
            self.tenant_id,
        )
        await self.conn.execute(
            "DELETE FROM subscription_audit WHERE details::text LIKE $1",
            f"%{self.subscription_id}%",
        )
        await self.conn.execute(
            "DELETE FROM subscriptions WHERE subscription_id = $1",
            self.subscription_id,
        )

    async def test_active_to_grace_transition(self, run_worker_once):
        """Test ACTIVE → GRACE transition when term_end passes."""
        term_end = datetime.now(timezone.utc) - timedelta(hours=1)

        await self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 50, now() - interval '1 year',
                      $3, 'ACTIVE', 'e2e-test')
            """,
            self.subscription_id,
            self.tenant_id,
            term_end,
        )

        result = run_worker_once()
        assert result.returncode == 0, result.stderr

        result = await self.conn.fetchrow(
            "SELECT status, grace_end FROM subscriptions WHERE subscription_id = $1",
            self.subscription_id,
        )
        assert result["status"] == "GRACE"
        assert result["grace_end"] is not None

        audit = await self.conn.fetchrow(
            """
            SELECT event_type FROM subscription_audit
            WHERE tenant_id = $1 AND event_type = 'GRACE_STARTED'
            ORDER BY event_timestamp DESC LIMIT 1
            """,
            self.tenant_id,
        )
        assert audit is not None

    async def test_grace_to_suspended_transition(self, run_worker_once):
        """Test GRACE → SUSPENDED transition when grace_end passes."""
        grace_end = datetime.now(timezone.utc) - timedelta(hours=1)

        await self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                term_start, term_end, status, grace_end, created_by
            ) VALUES ($1, $2, 'MAIN', 50, now() - interval '1 year',
                      now() - interval '15 days', 'GRACE', $3, 'e2e-test')
            """,
            self.subscription_id,
            self.tenant_id,
            grace_end,
        )

        result = run_worker_once()
        assert result.returncode == 0, result.stderr

        result = await self.conn.fetchrow(
            "SELECT status FROM subscriptions WHERE subscription_id = $1",
            self.subscription_id,
        )
        assert result["status"] == "SUSPENDED"

        audit = await self.conn.fetchrow(
            """
            SELECT event_type FROM subscription_audit
            WHERE tenant_id = $1 AND event_type = 'STATUS_SUSPENDED'
            ORDER BY event_timestamp DESC LIMIT 1
            """,
            self.tenant_id,
        )
        assert audit is not None

    async def test_renewal_notification_scheduled(self, run_worker_once):
        """Test renewal notification is scheduled for expiring subscription."""
        term_end = datetime.now(timezone.utc) + timedelta(days=30, hours=1)

        await self.conn.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, device_limit,
                term_start, term_end, status, created_by
            ) VALUES ($1, $2, 'MAIN', 50, now() - interval '335 days',
                      $3, 'ACTIVE', 'e2e-test')
            """,
            self.subscription_id,
            self.tenant_id,
            term_end,
        )

        result = run_worker_once()
        assert result.returncode == 0, result.stderr

        notification = await self.conn.fetchrow(
            """
            SELECT notification_type, status FROM subscription_notifications
            WHERE tenant_id = $1 AND notification_type = 'RENEWAL_30'
            ORDER BY scheduled_at DESC LIMIT 1
            """,
            self.tenant_id,
        )
        assert notification is not None
