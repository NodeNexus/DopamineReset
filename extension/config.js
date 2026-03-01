/**
 * config.js — loaded first by both popup.js and background.js
 *
 * The extension calls /api/config on the server to discover the
 * API base URL at runtime.  This means you only need to set
 * API_BASE_URL in the server's .env file — the extension never
 * needs to be rebuilt when the deployment URL changes.
 *
 * Cache the result in chrome.storage.local so subsequent calls
 * are instant and work even when the popup opens before the
 * background service-worker has fetched the config.
 *
 * BOOTSTRAP URL
 * ─────────────
 * The extension needs at least one URL to start.  Set this to
 * wherever your Flask server lives.  It is ONLY used for the
 * initial /api/config call — all subsequent traffic uses the URL
 * returned by that endpoint.
 */

const BOOTSTRAP_ORIGIN = "https://illusioned-svetlana-unguidedly.ngrok-free.dev";

/**
 * Returns the resolved API base URL.
 * First uses cached value from chrome.storage; if missing, fetches
 * /api/config from BOOTSTRAP_ORIGIN and caches the result.
 *
 * @returns {Promise<string>} e.g. "https://myapp.example.com"
 */
async function getApiBase() {
    const { apiBase } = await chrome.storage.local.get("apiBase");
    if (apiBase) return apiBase;

    try {
        const res = await fetch(`${BOOTSTRAP_ORIGIN}/api/config`, {
            cache: "no-store",
            headers: { "ngrok-skip-browser-warning": "true" }
        });
        const data = await res.json();
        const resolved = (data.api_base_url || BOOTSTRAP_ORIGIN).replace(/\/$/, "");
        await chrome.storage.local.set({ apiBase: resolved });
        return resolved;
    } catch {
        // Fallback: use the bootstrap origin itself
        return BOOTSTRAP_ORIGIN;
    }
}
