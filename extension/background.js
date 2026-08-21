/**
 * Previsor Steam — Background Service Worker
 * Compatível com Chrome, Opera e Brave (Manifest V3).
 *
 * Inicializa a URL padrão da API no chrome.storage.local
 * e faz o proxy de previsões para o content script (evita mixed content
 * HTTPS Steam → HTTP localhost).
 */

const CON_STR_DEFAULT_API_URL = "http://localhost:8000";
const CON_STR_DEFAULT_DASHBOARD_URL = "http://localhost:8501";
const CON_STR_DEFAULT_HORIZONTE = "latest";

chrome.runtime.onInstalled.addListener((details) => {
  console.log("[Previsor Steam] Extensão instalada:", details.reason);

  chrome.storage.local.get(["apiBaseUrl", "dashboardUrl", "horizonte"], (result) => {
    const var_objDefaults = {};
    if (!result.apiBaseUrl) {
      var_objDefaults.apiBaseUrl = CON_STR_DEFAULT_API_URL;
    }
    if (!result.dashboardUrl) {
      var_objDefaults.dashboardUrl = CON_STR_DEFAULT_DASHBOARD_URL;
    }
    if (!result.horizonte) {
      var_objDefaults.horizonte = CON_STR_DEFAULT_HORIZONTE;
    }
    if (Object.keys(var_objDefaults).length > 0) {
      chrome.storage.local.set(var_objDefaults, () => {
        console.log("[Previsor Steam] Configuração inicializada:", var_objDefaults);
      });
    }
  });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "PING") {
    sendResponse({ status: "PONG" });
    return true;
  }

  if (message.type === "PREDICT") {
    handlePredict(message.appId).then(sendResponse);
    return true;
  }

  return true;
});

/**
 * Consulta a API de previsão a partir do service worker.
 * @param {string} arg_strAppId
 * @returns {Promise<{ok: boolean, data?: object, error?: string}>}
 */
async function handlePredict(arg_strAppId) {
  if (!arg_strAppId) {
    return { ok: false, error: "AppID ausente" };
  }

  const var_objStored = await chrome.storage.local.get(["apiBaseUrl", "horizonte"]);
  const var_strApiBaseUrl = var_objStored.apiBaseUrl || CON_STR_DEFAULT_API_URL;
  const var_strHorizonte = var_objStored.horizonte || CON_STR_DEFAULT_HORIZONTE;

  try {
    const var_objResponse = await fetch(`${var_strApiBaseUrl}/predict/game`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: arg_strAppId, horizonte: var_strHorizonte }),
      signal: AbortSignal.timeout(15000),
    });

    if (var_objResponse.status === 404) {
      return { ok: false, error: `Jogo não encontrado: "${arg_strAppId}"` };
    }

    if (!var_objResponse.ok) {
      return { ok: false, error: `Erro na API (${var_objResponse.status})` };
    }

    const var_dictData = await var_objResponse.json();
    return { ok: true, data: var_dictData };
  } catch (err) {
    if (err.name === "AbortError" || err.name === "TimeoutError") {
      return { ok: false, error: "Timeout: a API demorou para responder" };
    }
    return { ok: false, error: "Não foi possível conectar à API" };
  }
}
