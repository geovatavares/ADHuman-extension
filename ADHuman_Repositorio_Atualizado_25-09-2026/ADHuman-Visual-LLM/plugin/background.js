"use strict";

const ADHUMAN_API_URL = "http://127.0.0.1:8000";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "ADHUMAN_BACKEND_REQUEST") return false;

  const path = String(message.path || "");
  const options = message.options || {};

  fetch(ADHUMAN_API_URL + path, options)
    .then(async (response) => {
      let payload = {};
      try {
        payload = await response.json();
      } catch (error) {
        payload = {};
      }
      if (!response.ok) {
        let detail = payload && payload.detail ? payload.detail : `HTTP ${response.status}`;
        if (typeof detail !== "string") detail = JSON.stringify(detail);
        throw new Error(detail);
      }
      sendResponse({ ok: true, payload });
    })
    .catch((error) => {
      sendResponse({
        ok: false,
        error: error && error.message ? error.message : String(error)
      });
    });

  return true;
});
