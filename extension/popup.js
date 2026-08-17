/**
 * Previsor Steam — Extension Popup Logic
 * Compatível com Chrome, Opera e Brave (Manifest V3).
 *
 * A URL da API é gerenciada via chrome.storage.local,
 * com fallback para http://localhost:8000 se não configurada.
 */

const CON_STR_DEFAULT_API_URL = "http://localhost:8000";

// Estado global da URL da API (carregado do storage)
let _var_strApiBaseUrl = CON_STR_DEFAULT_API_URL;
let _var_strCurrentAppId = null;

// ── DOM Elements ──
const elStatusDot = document.getElementById("statusDot");
const elLoading = document.getElementById("loading");
const elResults = document.getElementById("results");
const elError = document.getElementById("error");
const elErrorMsg = document.getElementById("errorMsg");
const elApiUrlInput = document.getElementById("apiUrlInput");
const elSaveApiBtn = document.getElementById("saveApiBtn");
const elSettingsToggle = document.getElementById("settingsToggle");
const elSettingsPanel = document.getElementById("settingsPanel");
const elHorizonSelect = document.getElementById("horizonSelect");
// ── Init ──
document.addEventListener("DOMContentLoaded", () => {
  carregarUrlApi();
  setupEventListeners();
  checkActiveTab();
});

/**
 * Lê a URL da aba ativa. Se for a loja da Steam, extrai o AppID.
 */
function checkActiveTab() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs.length > 0) {
      const var_strUrl = tabs[0].url;
      if (var_strUrl && var_strUrl.includes("store.steampowered.com/app/")) {
        const var_objMatch = var_strUrl.match(/\/app\/(\d+)/);
        if (var_objMatch && var_objMatch[1]) {
          _var_strCurrentAppId = var_objMatch[1];
          predict();
        }
      }
    }
  });
}

/**
 * Carrega a URL da API do chrome.storage.local.
 */
function carregarUrlApi() {
  chrome.storage.local.get(["apiBaseUrl"], (result) => {
    _var_strApiBaseUrl = result.apiBaseUrl || CON_STR_DEFAULT_API_URL;
    if (elApiUrlInput) {
      elApiUrlInput.value = _var_strApiBaseUrl;
    }
    // Atualiza o link da API Docs no footer
    const elApiLink = document.getElementById("apiLink");
    if (elApiLink) {
      elApiLink.href = `${_var_strApiBaseUrl}/docs`;
    }
    checkApiStatus();
  });
}

/**
 * Salva a URL da API no chrome.storage.local.
 */
function salvarUrlApi() {
  const var_strNewUrl = elApiUrlInput.value.trim().replace(/\/+$/, "");
  if (!var_strNewUrl) {
    showError("URL da API não pode ser vazia");
    return;
  }

  chrome.storage.local.set({ apiBaseUrl: var_strNewUrl }, () => {
    _var_strApiBaseUrl = var_strNewUrl;
    // Atualiza o link da API Docs
    const elApiLink = document.getElementById("apiLink");
    if (elApiLink) {
      elApiLink.href = `${var_strNewUrl}/docs`;
    }
    checkApiStatus();

    // Feedback visual
    elSaveApiBtn.textContent = "✅ Salvo!";
    setTimeout(() => {
      elSaveApiBtn.textContent = "💾 Salvar";
    }, 1500);
  });
}

function setupEventListeners() {
  // Horizon Select
  if (elHorizonSelect) {
    elHorizonSelect.addEventListener("change", () => {
      if (_var_strCurrentAppId) predict();
    });
  }

  // Settings toggle
  if (elSettingsToggle) {
    elSettingsToggle.addEventListener("click", () => {
      const var_boolVisible = elSettingsPanel.style.display === "block";
      elSettingsPanel.style.display = var_boolVisible ? "none" : "block";
    });
  }

  // Save API URL
  if (elSaveApiBtn) {
    elSaveApiBtn.addEventListener("click", salvarUrlApi);
  }
}

// ── API Health Check ──
async function checkApiStatus() {
  try {
    const var_objResponse = await fetch(`${_var_strApiBaseUrl}/health`, { signal: AbortSignal.timeout(3000) });
    const var_dictData = await var_objResponse.json();
    elStatusDot.classList.remove("offline");
    elStatusDot.classList.add("online");
    elStatusDot.title = `API Online • ${var_dictData.status}`;
  } catch {
    elStatusDot.classList.remove("online");
    elStatusDot.classList.add("offline");
    elStatusDot.title = "API Offline";
  }
}

// ── Predict ──
async function predict() {
  if (!_var_strCurrentAppId) {
    showError("Acesse a página de um jogo na Steam.");
    return;
  }

  showLoading();
  const var_strHorizon = elHorizonSelect ? elHorizonSelect.value : "latest";

  try {
    const var_objResponse = await fetch(`${_var_strApiBaseUrl}/predict/game`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: _var_strCurrentAppId, horizonte: var_strHorizon }),
      signal: AbortSignal.timeout(15000),
    });

    if (var_objResponse.status === 404) {
      showError(`Jogo não encontrado: "${_var_strCurrentAppId}"`);
      return;
    }

    if (!var_objResponse.ok) {
      showError(`Erro na API (${var_objResponse.status})`);
      return;
    }

    const var_dictData = await var_objResponse.json();
    showResults(var_dictData);
  } catch (err) {
    if (err.name === "AbortError" || err.name === "TimeoutError") {
      showError("Timeout: a API demorou para responder");
    } else {
      showError("Não foi possível conectar à API");
    }
  }
}

// ── Show Results ──
function showResults(arg_dictData) {
  hideAll();
  elResults.style.display = "block";

  const var_dictGame = arg_dictData.game || {};
  const var_dictClassificacao = arg_dictData.classificacao;
  const var_dictRegressao = arg_dictData.regressao;

  // Game info
  document.getElementById("gameName").textContent = var_dictGame.name || "Jogo";

  const elGameImage = document.getElementById("gameImage");
  if (var_dictGame.header_image) {
    elGameImage.src = var_dictGame.header_image;
    elGameImage.style.display = "block";
  } else {
    elGameImage.style.display = "none";
  }

  const var_floatPrice = var_dictGame.price || 0;
  document.getElementById("gamePrice").textContent =
    var_floatPrice > 0 ? `R$ ${var_floatPrice.toFixed(2)}` : "Gratuito";

  document.getElementById("gameReview").textContent =
    var_dictGame.review_score ? `⭐ ${var_dictGame.review_score}%` : "N/A";

  const elClassCard = document.getElementById("classCard");
  const elRegCard = document.getElementById("regCard");
  const elSaleCard = document.getElementById("saleCard");

  if (var_dictGame.is_on_sale) {
    elSaleCard.style.display = "block";
    elClassCard.style.display = "none";
    elRegCard.style.display = "none";

    document.getElementById("saleValue").textContent = `${var_dictGame.discount_percent}% de Desconto`;
    const var_strSaleEnd = var_dictGame.sale_end_date;
    if (var_strSaleEnd) {
      document.getElementById("saleDesc").textContent = `Término estimado: ${var_strSaleEnd}`;
    } else {
      document.getElementById("saleDesc").textContent = "A predição é abortada para jogos que já se encontram em promoção.";
    }
    return; // Early return visual
  } else {
    elSaleCard.style.display = "none";
  }

  // Classification
  if (var_dictClassificacao) {
    elClassCard.style.display = "block";

    const var_dictClassIcons = { cai: "📉", mantem: "➡️", sobe: "📈" };
    document.getElementById("classIcon").textContent = var_dictClassIcons[var_dictClassificacao.classe] || "📊";
    document.getElementById("classValue").textContent = var_dictClassificacao.classe_emoji || var_dictClassificacao.classe;

    // Confidence bar
    const var_intPct = Math.round(var_dictClassificacao.confianca * 100);
    document.getElementById("confidenceBar").style.width = `${var_intPct}%`;
    document.getElementById("confidenceValue").textContent = `${var_intPct}%`;

    // Probabilities
    const elProbContainer = document.getElementById("probabilities");
    elProbContainer.innerHTML = "";

    const var_dictProbColors = { cai: "cai", mantem: "mantem", sobe: "sobe" };

    if (var_dictClassificacao.probabilidades) {
      Object.entries(var_dictClassificacao.probabilidades).forEach(([var_strLabel, var_floatProb]) => {
        const var_intPctProb = Math.round(var_floatProb * 100);
        elProbContainer.innerHTML += `
          <div class="prob-row">
            <span class="prob-label">${var_strLabel}</span>
            <div class="prob-bar-container">
              <div class="prob-bar ${var_dictProbColors[var_strLabel] || ''}" style="width: ${var_intPctProb}%"></div>
            </div>
            <span class="prob-value">${var_intPctProb}%</span>
          </div>
        `;
      });
    }
  } else {
    elClassCard.style.display = "none";
  }

  // Regression
  if (var_dictRegressao) {
    elRegCard.style.display = "block";
    document.getElementById("regValue").textContent = `${var_dictRegressao.dias_estimados} dias`;
    document.getElementById("regDesc").textContent = var_dictRegressao.descricao;

    const elRegDetails = document.getElementById("regDetails");
    // Mostra o card de detalhes se houver predição de desconto
    if (var_dictRegressao.desconto_previsto_pct > 0) {
      elRegDetails.style.display = "block";
      document.getElementById("regDiscount").textContent = `${var_dictRegressao.desconto_previsto_pct}% OFF`;
      
      const var_floatPrecoEst = var_dictRegressao.preco_estimado;
      document.getElementById("regPrice").textContent = var_floatPrecoEst > 0 
        ? `R$ ${var_floatPrecoEst.toFixed(2)}` 
        : "Gratuito";
    } else {
      elRegDetails.style.display = "none";
    }
  } else {
    elRegCard.style.display = "none";
  }
}

// ── UI Helpers ──
function showLoading() {
  hideAll();
  elLoading.style.display = "flex";
}

function showError(arg_strMsg) {
  hideAll();
  elError.style.display = "flex";
  elErrorMsg.textContent = arg_strMsg;
}

function hideAll() {
  elLoading.style.display = "none";
  elResults.style.display = "none";
  elError.style.display = "none";
}
