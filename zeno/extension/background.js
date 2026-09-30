// ZENO Browser Extension — background.js (Manifest V3 Service Worker)
//
// WebSocket server: ws://localhost:8765
// PORT IS HARDCODED — if changed here, also change in zeno/monitor/ws_server.py (PORT constant).
//
// Message schema sent to Python server:
// tab_open:  { type: "tab_open",  browser, domain, page_title, url_category, started_at }
// tab_close: { type: "tab_close", domain, dwell_seconds }
// ping:      { type: "ping" }
//
// page_title is sent; redaction happens server-side per privacy_exclusions.

const WS_URL = "ws://localhost:8767";   // Must match zeno/monitor/ws_server.py PORT = 8767
const PING_INTERVAL_MS   = 30_000;
const RECONNECT_DELAY_MS = 5_000;
const MAX_RECONNECT_ATTEMPTS = 10;

function detectBrowser() {
  const ua = navigator.userAgent;
  if (ua.includes("Edg/"))     return "edge";
  if (ua.includes("Firefox/")) return "firefox";
  return "chrome";
}

// Domain → url_category mapping (server does final classification for unknowns)
const CATEGORY_PATTERNS = {
  work:     ["github.com", "gitlab.com", "jira.", "confluence.", "notion.so",
             "linear.app", "vercel.com", "figma.com"],
  research: ["stackoverflow.com", "docs.", "wikipedia.org", "developer.",
             "mdn.", "arxiv.org", "npmjs.com"],
  social:   ["twitter.com", "x.com", "reddit.com", "instagram.com",
             "facebook.com", "linkedin.com"],
  video:    ["youtube.com", "netflix.com", "twitch.tv", "vimeo.com"],
  news:     ["news.", "bbc.com", "cnn.com", "techcrunch.com"],
  email:    ["gmail.com", "outlook.", "mail.google.com", "proton.me"],
};

function categorize(domain) {
  const lower = domain.toLowerCase();
  for (const [cat, patterns] of Object.entries(CATEGORY_PATTERNS)) {
    if (patterns.some(p => lower.includes(p))) return cat;
  }
  return "unknown";
}

function extractDomain(url) {
  try { return new URL(url).hostname.replace(/^www\./, ""); }
  catch { return "unknown"; }
}

// ── WebSocket manager ──────────────────────────────────────────────────────

let ws = null;
let reconnectAttempts = 0;
let pingTimer = null;

function connect() {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.warn("[ZENO] Max reconnect attempts reached. Browser tracking paused.");
    return;
  }
  ws = new WebSocket(WS_URL);

  ws.addEventListener("open", () => {
    reconnectAttempts = 0;
    pingTimer = setInterval(() => send({ type: "ping" }), PING_INTERVAL_MS);
  });

  ws.addEventListener("close", () => {
    ws = null;
    clearInterval(pingTimer);
    pingTimer = null;
    reconnectAttempts++;
    setTimeout(connect, RECONNECT_DELAY_MS);
  });

  ws.addEventListener("error", () => { /* close event handles reconnect */ });
}

function send(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
  }
}

// ── Tab state machine ──────────────────────────────────────────────────────

// One active session at a time (the focused tab in the current window)
let activeSession = null;  // { tabId, domain, pageTitle, startedAt }

function openSession(tab) {
  if (!tab || !tab.url) return;
  // Skip browser internal pages
  if (tab.url.startsWith("chrome://") || tab.url.startsWith("about:") ||
      tab.url.startsWith("edge://")   || tab.url.startsWith("moz-extension://")) return;

  const domain = extractDomain(tab.url);
  activeSession = {
    tabId:     tab.id,
    domain,
    pageTitle: tab.title || "",
    startedAt: new Date().toISOString(),
  };
  send({
    type:         "tab_open",
    browser:      detectBrowser(),
    domain,
    page_title:   activeSession.pageTitle,
    url_category: categorize(domain),
    started_at:   activeSession.startedAt,
  });
}

function closeSession() {
  if (!activeSession) return;
  const dwellSeconds = Math.round(
    (Date.now() - new Date(activeSession.startedAt).getTime()) / 1000
  );
  send({ type: "tab_close", domain: activeSession.domain, dwell_seconds: dwellSeconds });
  activeSession = null;
}

// ── Chrome event listeners ─────────────────────────────────────────────────

chrome.tabs.onActivated.addListener(({ tabId }) => {
  closeSession();
  chrome.tabs.get(tabId, tab => {
    if (!chrome.runtime.lastError) openSession(tab);
  });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Only care about full-load completions on the active tab
  if (changeInfo.status === "complete" && tab.active) {
    closeSession();
    openSession(tab);
  }
});

chrome.tabs.onRemoved.addListener(tabId => {
  if (activeSession && activeSession.tabId === tabId) closeSession();
});

// Content script relay — visibility events
chrome.runtime.onMessage.addListener(message => {
  if (message.type === "page_hidden") closeSession();
  if (message.type === "page_visible") {
    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
      if (tabs[0]) openSession(tabs[0]);
    });
  }
});

// ── Startup ────────────────────────────────────────────────────────────────
connect();
