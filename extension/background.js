/**
 * Previsor Steam — Chrome Extension Background Service Worker
 */

// Listener para instalação
chrome.runtime.onInstalled.addListener((details) => {
  console.log("[Previsor Steam] Extensão instalada:", details.reason);
});

// Mantém o service worker ativo
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "PING") {
    sendResponse({ status: "PONG" });
  }
  return true;
});
