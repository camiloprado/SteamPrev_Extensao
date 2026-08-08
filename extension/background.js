/**
 * Previsor Steam — Background Service Worker
 * Compatível com Chrome, Opera e Brave (Manifest V3).
 *
 * Inicializa a URL padrão da API no chrome.storage.local
 * e responde a mensagens de ping do popup.
 */

const CON_STR_DEFAULT_API_URL = "http://localhost:8000";

// Listener para instalação — inicializa config padrão no storage
chrome.runtime.onInstalled.addListener((details) => {
  console.log("[Previsor Steam] Extensão instalada:", details.reason);

  // Define URL padrão da API no storage se não existir
  chrome.storage.local.get(["apiBaseUrl"], (result) => {
    if (!result.apiBaseUrl) {
      chrome.storage.local.set({ apiBaseUrl: CON_STR_DEFAULT_API_URL }, () => {
        console.log("[Previsor Steam] URL da API inicializada:", CON_STR_DEFAULT_API_URL);
      });
    }
  });
});

// Mantém o service worker ativo
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "PING") {
    sendResponse({ status: "PONG" });
  }
  return true;
});
