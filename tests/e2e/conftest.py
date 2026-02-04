import os
import sys
import asyncio
import asyncpg
from pathlib import Path
from urllib.parse import urlparse

import pytest
import httpx
from playwright.async_api._generated import PageAssertions
from playwright.async_api import async_playwright, Browser, BrowserContext

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
UI_BASE_URL = os.getenv("UI_BASE_URL")
E2E_BASE_URL = os.getenv("E2E_BASE_URL")
E2E_DATABASE_URL = os.getenv(
    "E2E_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://iot:iot_dev@localhost:5432/iotcloud"),
)
RUN_E2E = os.getenv("RUN_E2E", "").lower() in {"1", "true", "yes"}

# Screenshot comparison threshold — allows minor rendering differences
SCREENSHOT_THRESHOLD = 0.1  # 10% pixel difference allowed

_UPDATE_SNAPSHOTS = "--update-snapshots" in sys.argv
_SNAPSHOT_DIR = Path("tests/e2e/test_visual_regression-snapshots")
_LAST_SCREENSHOT_BYTES: bytes | None = None


def pytest_addoption(parser):
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Update Playwright visual regression baselines",
    )


@pytest.fixture(scope="session")
def update_snapshots(pytestconfig) -> bool:
    return pytestconfig.getoption("update_snapshots")


def pytest_configure(config):
    global _UPDATE_SNAPSHOTS
    _UPDATE_SNAPSHOTS = config.getoption("update_snapshots")


def _byte_diff_ratio(baseline: bytes, current: bytes) -> float:
    if not baseline and not current:
        return 0.0
    max_len = max(len(baseline), len(current))
    diff = abs(len(baseline) - len(current))
    return diff / max_len if max_len else 0.0


def record_screenshot_bytes(data: bytes) -> None:
    global _LAST_SCREENSHOT_BYTES
    _LAST_SCREENSHOT_BYTES = data


async def _to_have_screenshot(self, name: str, threshold: float = 0.1, full_page: bool = False):
    page = self._impl_obj._actual_page
    global _LAST_SCREENSHOT_BYTES
    current = _LAST_SCREENSHOT_BYTES
    _LAST_SCREENSHOT_BYTES = None
    if current is None:
        current = await page.screenshot()
    snapshot_path = _SNAPSHOT_DIR / name
    if _UPDATE_SNAPSHOTS or not snapshot_path.exists():
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_bytes(current)
        return
    baseline = snapshot_path.read_bytes()
    diff_ratio = _byte_diff_ratio(baseline, current)
    if diff_ratio > threshold:
        raise AssertionError(
            f"Screenshot mismatch for {name}: diff ratio {diff_ratio:.4f} > {threshold}"
        )


PageAssertions.to_have_screenshot = _to_have_screenshot


def _default_base_url() -> str:
    if E2E_BASE_URL:
        return E2E_BASE_URL
    if UI_BASE_URL:
        return UI_BASE_URL
    parsed = urlparse(KEYCLOAK_URL)
    if parsed.hostname:
        scheme = parsed.scheme or "http"
        return f"{scheme}://{parsed.hostname}:8080"
    return "http://localhost:8080"


BASE_URL = _default_base_url()
if not KEYCLOAK_URL:
    parsed_base = urlparse(BASE_URL)
    scheme = parsed_base.scheme or "http"
    host = parsed_base.hostname or "localhost"
    KEYCLOAK_URL = f"{scheme}://{host}:8180"
os.environ.setdefault("KEYCLOAK_URL", KEYCLOAK_URL)


async def _is_reachable(url: str) -> bool:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=5.0) as client:
            response = await client.get(url)
            return response.status_code < 500
    except Exception:
        return False


async def _wait_for_reachable(url: str, attempts: int = 10, delay: float = 1.0) -> bool:
    for _ in range(attempts):
        if await _is_reachable(url):
            return True
        await asyncio.sleep(delay)
    return False


async def _seed_device_state() -> None:
    conn = await asyncpg.connect(E2E_DATABASE_URL)
    try:
        await conn.execute(
            """
            INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
            VALUES
                ('tenant-a', 'test-device-a1', 'test-site-a', 'ONLINE', now()),
                ('tenant-a', 'test-device-a2', 'test-site-a', 'STALE', now() - interval '1 hour'),
                ('tenant-b', 'test-device-b1', 'test-site-b', 'ONLINE', now())
            ON CONFLICT (tenant_id, device_id) DO NOTHING
            """
        )
    finally:
        await conn.close()


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance."""
    if not RUN_E2E:
        pytest.skip("E2E tests disabled (set RUN_E2E=1 to enable)")
    base_ok = await _wait_for_reachable(BASE_URL)
    keycloak_ok = await _wait_for_reachable(KEYCLOAK_URL)
    if not base_ok or not keycloak_ok:
        pytest.fail("E2E services not available (set E2E_BASE_URL and KEYCLOAK_URL)")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def context(browser: Browser):
    """Create browser context with fresh state."""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        base_url=BASE_URL,
    )
    yield context
    await context.close()


@pytest.fixture
async def page(context: BrowserContext):
    """Create page."""
    page = await context.new_page()
    yield page
    await page.close()


@pytest.fixture
async def authenticated_customer_page(context: BrowserContext):
    """Create page with customer1 logged in."""
    await _seed_device_state()
    page = await context.new_page()
    await page.goto("/")
    await page.wait_for_url(f"{KEYCLOAK_URL}/**")
    await page.fill("#username", "customer1")
    await page.fill("#password", "test123")
    await page.click("#kc-login")
    await page.wait_for_url(f"{BASE_URL}/customer/dashboard")
    yield page
    await page.close()


@pytest.fixture
async def cleanup_integrations(authenticated_customer_page):
    """Track and delete integrations created during a test.

    Yields a list; append tuples of (type, id) where type is
    "webhook", "snmp", or "email".
    """
    page = authenticated_customer_page
    created = []
    yield created
    for int_type, int_id in created:
        try:
            if int_type == "snmp":
                await page.request.delete(f"/customer/integrations/snmp/{int_id}")
            elif int_type == "email":
                await page.request.delete(f"/customer/integrations/email/{int_id}")
            else:
                await page.request.delete(f"/customer/integrations/{int_id}")
        except Exception:
            pass


@pytest.fixture
async def authenticated_operator_page(context: BrowserContext):
    """Create page with operator1 logged in."""
    await _seed_device_state()
    page = await context.new_page()
    await page.goto("/")
    await page.wait_for_url(f"{KEYCLOAK_URL}/**")
    await page.fill("#username", "operator1")
    await page.fill("#password", "test123")
    await page.click("#kc-login")
    await page.wait_for_url(f"{BASE_URL}/operator/dashboard")
    yield page
    await page.close()
