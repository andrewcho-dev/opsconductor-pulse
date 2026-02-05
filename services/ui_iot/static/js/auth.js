window._tokenExpiresAt = 0;
window._refreshIntervalId = null;

async function checkAuthStatus() {
  try {
    const resp = await fetch("/api/auth/status", { credentials: "include" });
    if (!resp.ok) {
      return { authenticated: false };
    }
    return await resp.json();
  } catch (err) {
    return { authenticated: false };
  }
}

async function refreshToken() {
  try {
    const resp = await fetch("/api/auth/refresh", {
      method: "POST",
      credentials: "include",
    });
    if (!resp.ok) {
      return { success: false };
    }
    return await resp.json();
  } catch (err) {
    return { success: false };
  }
}

function redirectToLogin() {
  window.location = "/";
}

function scheduleRefresh(expiresIn) {
  window._tokenExpiresAt = Date.now() + expiresIn * 1000;
  if (window._refreshIntervalId !== null) {
    clearInterval(window._refreshIntervalId);
  }
  window._refreshIntervalId = setInterval(maybeRefresh, 30000);
}

async function maybeRefresh() {
  if (Date.now() > window._tokenExpiresAt - 90000) {
    const result = await refreshToken();
    if (result && result.success) {
      scheduleRefresh(result.expires_in || 900);
      return;
    }
    await new Promise((r) => setTimeout(r, 5000));
    const retry = await refreshToken();
    if (retry && retry.success) {
      scheduleRefresh(retry.expires_in || 900);
      return;
    }
    redirectToLogin();
  }
}

function setupVisibilityListener() {
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") {
      maybeRefresh();
    }
  });
}

function setupFetchInterceptor() {
  const _originalFetch = window.fetch;
  window.fetch = async function (...args) {
    const response = await _originalFetch.apply(this, args);
    const url = args[0] ? args[0].toString() : "";
    if (response.status === 401 && !url.includes("/api/auth/")) {
      const result = await refreshToken();
      if (result && result.success) {
        return _originalFetch.apply(this, args);
      }
      redirectToLogin();
    }
    return response;
  };
}

document.addEventListener("DOMContentLoaded", async () => {
  const status = await checkAuthStatus();
  if (!status.authenticated) {
    redirectToLogin();
    return;
  }
  scheduleRefresh(status.expires_in || 900);
  setupVisibilityListener();
  setupFetchInterceptor();
});
