// popup.js — handles login / logout UI for the Dopamine Reset extension
// API base URL is resolved from the server's .env via getApiBase() in config.js

const statusEl = document.getElementById("status");
const loginBox = document.getElementById("loginBox");
const loggedBox = document.getElementById("loggedBox");
const consentBox = document.getElementById("consentBox");
const consentCheck = document.getElementById("telemetryConsent");

const usernameEl = document.getElementById("username");
const passEl = document.getElementById("password");

// Register link — opens the /register page on the configured server
document.getElementById("registerLink").addEventListener("click", async () => {
    const apiBase = await getApiBase();
    chrome.tabs.create({ url: `${apiBase}/register` });
});

async function render() {
    const { accessToken, username, telemetryConsent } = await chrome.storage.local.get(["accessToken", "username", "telemetryConsent"]);

    if (telemetryConsent) {
        consentCheck.checked = true;
    }

    const logged = !!accessToken;
    statusEl.textContent = logged ? `Logged in as ${username}` : "Not logged in";
    loginBox.style.display = logged ? "none" : "block";
    consentBox.style.display = logged ? "none" : "block";
    loggedBox.style.display = logged ? "block" : "none";
}

consentCheck.addEventListener("change", async () => {
    await chrome.storage.local.set({ telemetryConsent: consentCheck.checked });
});

document.getElementById("loginBtn").addEventListener("click", async () => {
    if (!consentCheck.checked) {
        statusEl.textContent = "You must consent to telemetry to continue.";
        return;
    }

    const username = (usernameEl.value || "").trim();
    const password = passEl.value || "";

    if (!username || !password) {
        statusEl.textContent = "Username and password required.";
        return;
    }

    statusEl.textContent = "Logging in...";

    try {
        // Always resolve the URL from the server's .env (clears stale cache too)
        await chrome.storage.local.remove("apiBase"); // force fresh fetch on login
        const apiBase = await getApiBase();

        const res = await fetch(`${apiBase}/api/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (!res.ok) {
            statusEl.textContent = data.error || "Login failed";
            return;
        }

        await chrome.storage.local.set({
            username: username,
            accessToken: data.access_token,
            telemetryConsent: true
        });

        statusEl.textContent = "✅ Login successful";
        await render();
    } catch (e) {
        statusEl.textContent = "Backend not reachable.";
    }
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
    await chrome.storage.local.remove(["accessToken", "username"]);
    statusEl.textContent = "Logged out.";
    await render();
});

render();
