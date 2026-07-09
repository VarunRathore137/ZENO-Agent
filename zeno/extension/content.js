// ZENO Browser Extension — content.js
// Reports page visibility changes to the background service worker.
// Injected into every page (document_start). Minimal footprint — event listener only.

document.addEventListener("visibilitychange", () => {
  chrome.runtime.sendMessage({
    type: document.hidden ? "page_hidden" : "page_visible"
  });
});
