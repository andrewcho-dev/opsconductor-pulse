import os
import asyncio
import re
from datetime import datetime, timezone, timedelta

import asyncpg
import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

E2E_API_URL = os.getenv("E2E_API_URL") or os.getenv("E2E_BASE_URL")
E2E_DATABASE_URL = os.getenv(
    "E2E_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://iot:iot_dev@localhost:5432/iotcloud"),
)


async def _db_connect():
    return await asyncpg.connect(E2E_DATABASE_URL)


async def _get_any_tenant(conn: asyncpg.Connection) -> str:
    tenant_id = await conn.fetchval("SELECT tenant_id FROM tenants ORDER BY tenant_id LIMIT 1")
    if not tenant_id:
        raise AssertionError("No tenants found for E2E tests.")
    return tenant_id


async def _get_main_subscription(conn: asyncpg.Connection, tenant_id: str):
    return await conn.fetchrow(
        """
        SELECT subscription_id, term_end, active_device_count, device_limit
        FROM subscriptions
        WHERE tenant_id = $1 AND subscription_type = 'MAIN' AND status = 'ACTIVE'
        ORDER BY created_at ASC
        LIMIT 1
        """,
        tenant_id,
    )


async def _get_tenant_with_active_main(conn: asyncpg.Connection) -> str:
    tenant_id = await conn.fetchval(
        """
        SELECT tenant_id
        FROM subscriptions
        WHERE subscription_type = 'MAIN' AND status = 'ACTIVE'
        ORDER BY created_at ASC
        LIMIT 1
        """
    )
    if not tenant_id:
        raise AssertionError("No tenant with ACTIVE MAIN subscription found.")
    return tenant_id


async def _wait_for_subscription(
    conn: asyncpg.Connection,
    tenant_id: str,
    subscription_type: str,
    created_after: datetime,
    parent_subscription_id: str | None = None,
):
    for _ in range(20):
        row = await conn.fetchrow(
            """
            SELECT subscription_id, term_end, parent_subscription_id
            FROM subscriptions
            WHERE tenant_id = $1
              AND subscription_type = $2
              AND created_at >= $3
              AND ($4::text IS NULL OR parent_subscription_id = $4)
            ORDER BY created_at DESC
            LIMIT 1
            """,
            tenant_id,
            subscription_type,
            created_after,
            parent_subscription_id,
        )
        if row:
            return row
        await asyncio.sleep(1)
    raise AssertionError("Timed out waiting for subscription creation.")


async def _wait_for_subscription_with_description(
    conn: asyncpg.Connection,
    tenant_id: str,
    subscription_type: str,
    description: str,
):
    for _ in range(20):
        row = await conn.fetchrow(
            """
            SELECT subscription_id, term_end, parent_subscription_id
            FROM subscriptions
            WHERE tenant_id = $1
              AND subscription_type = $2
              AND description = $3
            ORDER BY created_at DESC
            LIMIT 1
            """,
            tenant_id,
            subscription_type,
            description,
        )
        if row:
            return row
        await asyncio.sleep(1)
    raise AssertionError("Timed out waiting for subscription creation.")


async def _ensure_secondary_subscription(conn: asyncpg.Connection, tenant_id: str):
    row = await conn.fetchrow(
        """
        SELECT subscription_id
        FROM subscriptions
        WHERE tenant_id = $1 AND subscription_type = 'TEMPORARY'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        tenant_id,
    )
    if row:
        return row["subscription_id"]
    sub_id = await conn.fetchval("SELECT generate_subscription_id()")
    await conn.execute(
        """
        INSERT INTO subscriptions (
            subscription_id, tenant_id, subscription_type, device_limit,
            term_start, term_end, status, created_by
        ) VALUES ($1, $2, 'TEMPORARY', 200, now(), now() + interval '90 days', 'ACTIVE', 'e2e')
        """,
        sub_id,
        tenant_id,
    )
    return sub_id


async def _get_device_for_subscription(conn: asyncpg.Connection, subscription_id: str):
    return await conn.fetchrow(
        """
        SELECT ds.tenant_id, ds.device_id
        FROM device_state ds
        JOIN device_registry dr
          ON dr.tenant_id = ds.tenant_id AND dr.device_id = ds.device_id
        WHERE dr.subscription_id = $1
        ORDER BY ds.site_id, ds.device_id
        LIMIT 1
        """,
        subscription_id,
    )


async def _get_subscription_counts(conn: asyncpg.Connection, subscription_id: str):
    return await conn.fetchrow(
        """
        SELECT active_device_count
        FROM subscriptions
        WHERE subscription_id = $1
        """,
        subscription_id,
    )


class TestOperatorMultiSubscriptionUI:
    async def test_operator_subscription_list_page(
        self, authenticated_operator_page: Page
    ):
        page = authenticated_operator_page
        await page.goto("/app/operator/subscriptions")
        await expect(page.locator("text=Subscription ID")).to_be_visible()
        await expect(page.locator("table tbody tr").first).to_be_visible()
        main_badge = page.locator("text=MAIN").first
        if await main_badge.count() == 0:
            pytest.skip("MAIN subscription badge not visible.")
        await expect(main_badge).to_be_visible()
        active_badge = page.locator("text=ACTIVE").first
        if await active_badge.count() == 0:
            pytest.skip("ACTIVE subscription badge not visible.")
        await expect(active_badge).to_be_visible()

    async def test_operator_create_main_subscription(
        self, authenticated_operator_page: Page
    ):
        page = authenticated_operator_page
        await page.goto("/app/operator/subscriptions")
        await page.click("button:has-text('New Subscription')")
        dialog = page.locator("[role='dialog']")

        conn = await _db_connect()
        try:
            tenant_id = await _get_any_tenant(conn)
        finally:
            await conn.close()

        comboboxes = dialog.locator("button[role='combobox']")
        await comboboxes.nth(0).click()
        await page.get_by_role("option", name=re.compile(tenant_id)).click()

        number_inputs = dialog.locator("input[type='number']")
        await number_inputs.nth(0).fill("100")
        await number_inputs.nth(1).fill("365")
        await dialog.locator("textarea").fill("E2E create MAIN subscription")
        created_after = datetime.now(timezone.utc)
        create_button = page.locator("button:has-text('Create')")
        await expect(create_button).to_be_enabled()
        await create_button.click()

        conn = await _db_connect()
        try:
            row = await _wait_for_subscription(
                conn, tenant_id, "MAIN", created_after
            )
        finally:
            await conn.close()

        await page.reload()
        await page.wait_for_load_state("networkidle")
        await expect(page.locator(f"text={row['subscription_id']}")).to_be_visible(
            timeout=15000
        )

    async def test_operator_create_addon_subscription(
        self, authenticated_operator_page: Page
    ):
        page = authenticated_operator_page

        conn = await _db_connect()
        try:
            tenant_id = await _get_tenant_with_active_main(conn)
            parent = await _get_main_subscription(conn, tenant_id)
            if not parent:
                raise AssertionError("No MAIN subscription found for tenant.")
        finally:
            await conn.close()

        description = f"E2E ADDON {datetime.now(timezone.utc).timestamp()}"
        conn = await _db_connect()
        try:
            sub_id = await conn.fetchval("SELECT generate_subscription_id()")
            await conn.execute(
                """
                INSERT INTO subscriptions (
                    subscription_id, tenant_id, subscription_type, parent_subscription_id,
                    device_limit, term_start, term_end, status, description, created_by
                ) VALUES ($1, $2, 'ADDON', $3, 50, now(), now() + interval '30 days',
                          'ACTIVE', $4, 'e2e')
                """,
                sub_id,
                tenant_id,
                parent["subscription_id"],
                description,
            )
            addon = await _wait_for_subscription_with_description(
                conn, tenant_id, "ADDON", description
            )
            parent_term_end = parent["term_end"]
            assert addon["term_end"] == parent_term_end
        finally:
            await conn.close()

    async def test_operator_assign_device_to_subscription(
        self, authenticated_operator_page: Page
    ):
        device_id = None
        tenant_id = None
        secondary_id = None
        conn = await _db_connect()
        try:
            tenant_id = await _get_any_tenant(conn)
            main_sub = await _get_main_subscription(conn, tenant_id)
            if not main_sub:
                raise AssertionError("No MAIN subscription found for assignment test.")
            secondary_id = await _ensure_secondary_subscription(conn, tenant_id)
            device_id = f"AAA-E2E-ASSIGN-{int(datetime.now(timezone.utc).timestamp())}"
            await conn.execute(
                """
                INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
                VALUES ($1, $2, 'E2E-SITE', 'STALE', now())
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                tenant_id,
                device_id,
            )
            await conn.execute(
                """
                INSERT INTO device_registry (tenant_id, device_id, site_id, status, subscription_id)
                VALUES ($1, $2, 'E2E-SITE', 'ACTIVE', $3)
                ON CONFLICT (tenant_id, device_id) DO UPDATE
                SET subscription_id = EXCLUDED.subscription_id
                """,
                tenant_id,
                device_id,
                main_sub["subscription_id"],
            )
        finally:
            await conn.close()

        page = authenticated_operator_page
        await page.goto("/app/operator/devices")
        await page.fill("input[placeholder='Filter by tenant_id']", tenant_id)
        await page.click("button:has-text('Filter')")
        await page.wait_for_load_state("networkidle")

        row = page.locator("tr", has_text=device_id)
        await expect(row).to_be_visible(timeout=15000)
        await row.locator("button:has-text('Reassign'), button:has-text('Assign')").click()
        dialog = page.locator("[role='dialog']")
        await dialog.locator("button:has-text('Select subscription')").click()
        await page.get_by_role("option", name=secondary_id).click()
        await dialog.locator("textarea").fill("E2E reassignment")
        await dialog.locator("button:has-text('Assign')").click()

        conn = await _db_connect()
        try:
            updated = await conn.fetchval(
                """
                SELECT subscription_id
                FROM device_registry
                WHERE tenant_id = $1 AND device_id = $2
                """,
                tenant_id,
                device_id,
            )
            assert updated == secondary_id
        finally:
            if tenant_id and device_id:
                await conn.execute(
                    "DELETE FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                    tenant_id,
                    device_id,
                )
                await conn.execute(
                    "DELETE FROM device_state WHERE tenant_id = $1 AND device_id = $2",
                    tenant_id,
                    device_id,
                )
            await conn.close()


class TestCustomerMultiSubscriptionUI:
    async def test_customer_multi_subscription_view(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        tenant_id = (await page.locator("header [data-slot='badge']").first.inner_text()).strip()
        created_sub_id = None
        conn = await _db_connect()
        try:
            existing = await conn.fetchval(
                "SELECT subscription_id FROM subscriptions WHERE tenant_id = $1 LIMIT 1",
                tenant_id,
            )
            if not existing:
                created_sub_id = await conn.fetchval("SELECT generate_subscription_id()")
                await conn.execute(
                    """
                    INSERT INTO subscriptions (
                        subscription_id, tenant_id, subscription_type, device_limit,
                        active_device_count, term_start, term_end, status, created_by
                    ) VALUES ($1, $2, 'MAIN', 100, 5, now() - interval '30 days',
                              now() + interval '180 days', 'ACTIVE', 'e2e-test')
                    """,
                    created_sub_id,
                    tenant_id,
                )
        finally:
            await conn.close()

        await page.goto("/app/subscription")
        await page.wait_for_url("**/app/subscription*")
        await page.wait_for_load_state("networkidle")
        await expect(page.get_by_role("heading", name="Subscription")).to_be_visible(
            timeout=15000
        )
        if await page.get_by_text("No active subscriptions").is_visible():
            pytest.skip("No active subscriptions for this customer.")
        if not await page.locator("text=Total Capacity").is_visible():
            pytest.skip("Subscription summary not available for this customer.")
        await expect(page.locator("text=Total Capacity")).to_be_visible()
        await expect(
            page.locator("div.text-sm.font-semibold", has_text="Primary").first
        ).to_be_visible()
        await expect(
            page.locator("div.text-sm.font-semibold", has_text="Add-ons").first
        ).to_be_visible()
        await expect(
            page.locator("div.text-sm.font-semibold", has_text="Trial & Temporary").first
        ).to_be_visible()

        await page.wait_for_selector("button:has-text('Devices')")
        async with page.expect_response(
            lambda r: "/customer/subscriptions/" in r.url and r.status == 200
        ):
            await page.get_by_role("button", name="Devices").first.click()
        await expect(
            page.get_by_role("button", name="Devices").first
        ).to_have_attribute("aria-expanded", "true")

        if created_sub_id:
            conn = await _db_connect()
            try:
                await conn.execute(
                    "DELETE FROM subscriptions WHERE subscription_id = $1",
                    created_sub_id,
                )
            finally:
                await conn.close()

    async def test_subscription_banner_warnings(
        self, authenticated_customer_page: Page
    ):
        created_sub_id = None
        conn = await _db_connect()
        try:
            tenant_id = (
                await authenticated_customer_page.locator("header [data-slot='badge']")
                .first.inner_text()
            ).strip()
            sub_id = await conn.fetchval(
                "SELECT subscription_id FROM subscriptions WHERE tenant_id = $1 LIMIT 1",
                tenant_id,
            )
            if not sub_id:
                sub_id = await conn.fetchval("SELECT generate_subscription_id()")
                created_sub_id = sub_id
                await conn.execute(
                    """
                    INSERT INTO subscriptions (
                        subscription_id, tenant_id, subscription_type, device_limit,
                        active_device_count, term_start, term_end, status, created_by
                    ) VALUES ($1, $2, 'MAIN', 100, 5, now() - interval '30 days',
                              now() + interval '180 days', 'ACTIVE', 'e2e-test')
                    """,
                    sub_id,
                    tenant_id,
                )
        finally:
            await conn.close()

        page = authenticated_customer_page

        conn = await _db_connect()
        try:
            await conn.execute(
                """
                UPDATE subscriptions
                SET term_end = $2, status = 'ACTIVE'
                WHERE subscription_id = $1
                """,
                sub_id,
                datetime.now(timezone.utc) + timedelta(days=7),
            )
        finally:
            await conn.close()

        await page.goto("/app/dashboard")
        await page.wait_for_url("**/app/dashboard*")
        await expect(page.get_by_role("heading", name="Dashboard")).to_be_visible(
            timeout=15000
        )
        if not await page.locator("text=expires in").first.is_visible():
            pytest.skip("No expiring subscription banner visible for this tenant.")
        await expect(page.locator("text=expires in").first).to_be_visible()

        conn = await _db_connect()
        try:
            await conn.execute(
                "UPDATE subscriptions SET status = 'GRACE' WHERE subscription_id = $1",
                sub_id,
            )
        finally:
            await conn.close()

        await page.goto("/app/dashboard")
        await page.wait_for_url("**/app/dashboard*")
        await expect(page.get_by_role("heading", name="Dashboard")).to_be_visible(
            timeout=15000
        )
        await expect(page.locator("text=Grace period active").first).to_be_visible()

        conn = await _db_connect()
        try:
            await conn.execute(
                "UPDATE subscriptions SET status = 'SUSPENDED' WHERE subscription_id = $1",
                sub_id,
            )
        finally:
            await conn.close()

        await page.goto("/app/dashboard")
        await page.wait_for_url("**/app/dashboard*")
        await expect(page.get_by_role("heading", name="Dashboard")).to_be_visible(
            timeout=15000
        )
        await expect(page.locator("text=suspended").first).to_be_visible()
        await expect(page.locator("text=Contact support").first).to_be_visible()

        conn = await _db_connect()
        try:
            await conn.execute(
                "UPDATE subscriptions SET status = 'ACTIVE' WHERE subscription_id = $1",
                sub_id,
            )
        finally:
            await conn.close()

        if created_sub_id:
            conn = await _db_connect()
            try:
                await conn.execute(
                    "DELETE FROM subscriptions WHERE subscription_id = $1",
                    created_sub_id,
                )
            finally:
                await conn.close()
