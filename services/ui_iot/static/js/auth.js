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

function scheduleRefresh(expiresIn) {
  const refreshIn = Math.max(5, expiresIn - 60);
  window.setTimeout(async () => {
    const result = await refreshToken();
    if (result && result.success) {
      scheduleRefresh(result.expires_in || 300);
    } else {
      redirectToLogin();
    }
  }, refreshIn * 1000);
}

function redirectToLogin() {
  window.location = "/";
}

document.addEventListener("DOMContentLoaded", async () => {
  const status = await checkAuthStatus();
  if (!status.authenticated) {
    redirectToLogin();
    return;
  }
  scheduleRefresh(status.expires_in || 300);
});
