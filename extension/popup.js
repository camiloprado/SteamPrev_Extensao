/**
 * Previsor Steam — Extension Popup Logic
 * Compatível com Chrome, Opera e Brave (Manifest V3).
 *
 * A URL da API e do dashboard são gerenciadas via chrome.storage.local,
 * com fallback para localhost se não configuradas.
 */

const CON_STR_DEFAULT_API_URL = "http://localhost:8000";
const CON_STR_DEFAULT_DASHBOARD_URL = "http://localhost:8501";
const CON_STR_DOCKER_UP_CMD = "docker compose up -d api";
const CON_STR_BTN_CHECK_LABEL = "🔌 Verificar / ligar API";
const CON_INT_STATUS_POLL_MS = 5000;

// Estado global das URLs (carregado do storage)
let _var_strApiBaseUrl = CON_STR_DEFAULT_API_URL;
let _var_strDashboardUrl = CON_STR_DEFAULT_DASHBOARD_URL;
let _var_strCurrentAppId = null;

// ── DOM Elements ──
const elStatusDot = document.getElementById("statusDot");
const elLoading = document.getElementById("loading");
const elResults = document.getElementById("results");
const elError = document.getElementById("error");
const elErrorMsg = document.getElementById("errorMsg");
const elApiUrlInput = document.getElementById("apiUrlInput");
const elSaveApiBtn = document.getElementById("saveApiBtn");
const elDashboardUrlInput = document.getElementById("dashboardUrlInput");
const elSaveDashboardBtn = document.getElementById("saveDashboardBtn");
const elOpenDashboardBtn = document.getElementById("openDashboardBtn");
const elSettingsToggle = document.getElementById("settingsToggle");
const elSettingsPanel = document.getElementById("settingsPanel");
const elHorizonSelect = document.getElementById("horizonSelect");
const elThemeToggle = document.getElementById("themeToggle");
const elCheckApiBtn = document.getElementById("checkApiBtn");
const elApiHelpPanel = document.getElementById("apiHelpPanel");
const elApiHelpLead = document.getElementById("apiHelpLead");
const elApiHelpStepsLocal = document.getElementById("apiHelpStepsLocal");
const elApiHelpStepsRemote = document.getElementById("apiHelpStepsRemote");
const elApiHelpNote = document.getElementById("apiHelpNote");
const elApiHelpCommand = document.getElementById("apiHelpCommand");
const elCopyCmdBtn = document.getElementById("copyCmdBtn");
const elApiHelpDocsLink = document.getElementById("apiHelpDocsLink");
let _var_intBtnFeedbackTimer = null;
let _var_boolCheckingApi = false;

// ── Init ──
document.addEventListener("DOMContentLoaded", () => {
  inicializarTema();
  carregarUrlApi();
  setupEventListeners();
});

/**
 * Aplica o tema (claro/escuro) na página e atualiza o ícone da toolbar.
 * Sem preferência salva, segue o tema do sistema operacional.
 */
function inicializarTema() {
  chrome.storage.local.get(["theme"], (result) => {
    const var_strTemaSalvo = result.theme || null; // "light" | "dark" | null (auto)
    aplicarTema(var_strTemaSalvo);

    // Acompanha mudanças do SO em tempo real enquanto não houver escolha manual
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      chrome.storage.local.get(["theme"], (r) => {
        if (!r.theme) aplicarTema(null);
      });
    });
  });

  if (elThemeToggle) {
    elThemeToggle.addEventListener("click", () => {
      const var_strTemaEfetivo = document.documentElement.getAttribute("data-theme") || temaDoSistema();
      const var_strNovoTema = var_strTemaEfetivo === "dark" ? "light" : "dark";
      chrome.storage.local.set({ theme: var_strNovoTema }, () => aplicarTema(var_strNovoTema));
    });
  }
}

function temaDoSistema() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/**
 * @param {"light"|"dark"|null} arg_strTema - null = seguir o sistema
 */
function aplicarTema(arg_strTema) {
  const var_strEfetivo = arg_strTema || temaDoSistema();
  document.documentElement.setAttribute("data-theme", var_strEfetivo);

  if (elThemeToggle) {
    elThemeToggle.textContent = var_strEfetivo === "dark" ? "🌙" : "☀️";
    elThemeToggle.title = var_strEfetivo === "dark" ? "Tema escuro (clique para claro)" : "Tema claro (clique para escuro)";
  }

  atualizarIconeToolbar(var_strEfetivo);
}

/**
 * Troca o ícone da toolbar para a variante que contrasta com o tema ativo
 * (Chrome/Opera/Brave não suportam troca automática via manifest).
 */
function atualizarIconeToolbar(arg_strTema) {
  if (!chrome.action || !chrome.action.setIcon) return;
  const var_strPasta = arg_strTema === "dark" ? "icons/dark" : "icons";
  chrome.action.setIcon({
    path: {
      16: `${var_strPasta}/icon16.png`,
      48: `${var_strPasta}/icon48.png`,
      128: `${var_strPasta}/icon128.png`,
    },
  });
}

/**
 * Extrai o AppID de URLs da loja, inclusive com locale (/pt-br/app/123).
 */
function extrairAppId(arg_strUrl) {
  if (!arg_strUrl || !arg_strUrl.includes("store.steampowered.com")) return null;
  const var_objMatch = arg_strUrl.match(/\/app\/(\d+)/);
  return var_objMatch ? var_objMatch[1] : null;
}

/**
 * Lê a URL da aba ativa. Se for a loja da Steam, extrai o AppID.
 */
function checkActiveTab() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs.length > 0) {
      _var_strCurrentAppId = extrairAppId(tabs[0].url);
      if (_var_strCurrentAppId) predict();
    }
  });
}

/**
 * Carrega URLs (API + dashboard) e horizonte do chrome.storage.local.
 */
function carregarUrlApi() {
  chrome.storage.local.get(["apiBaseUrl", "dashboardUrl", "horizonte"], (result) => {
    _var_strApiBaseUrl = result.apiBaseUrl || CON_STR_DEFAULT_API_URL;
    _var_strDashboardUrl = result.dashboardUrl || CON_STR_DEFAULT_DASHBOARD_URL;
    if (elApiUrlInput) {
      elApiUrlInput.value = _var_strApiBaseUrl;
    }
    if (elDashboardUrlInput) {
      elDashboardUrlInput.value = _var_strDashboardUrl;
    }
    if (elHorizonSelect && result.horizonte) {
      elHorizonSelect.value = result.horizonte;
    }
    atualizarLinksDocs();
    checkApiStatus();
    checkActiveTab();
    setInterval(checkApiStatus, CON_INT_STATUS_POLL_MS);
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
    atualizarLinksDocs();
    checkApiStatus();

    // Feedback visual
    elSaveApiBtn.textContent = "✅ Salvo!";
    setTimeout(() => {
      elSaveApiBtn.textContent = "💾 Salvar";
    }, 1500);
  });
}

/**
 * Salva a URL do dashboard Streamlit no chrome.storage.local.
 */
function salvarUrlDashboard() {
  if (!elDashboardUrlInput) return;
  const var_strNewUrl = elDashboardUrlInput.value.trim().replace(/\/+$/, "");
  if (!var_strNewUrl) {
    showError("URL do dashboard não pode ser vazia");
    return;
  }

  chrome.storage.local.set({ dashboardUrl: var_strNewUrl }, () => {
    _var_strDashboardUrl = var_strNewUrl;
    if (elSaveDashboardBtn) {
      elSaveDashboardBtn.textContent = "✅ Salvo!";
      setTimeout(() => {
        elSaveDashboardBtn.textContent = "💾 Salvar";
      }, 1500);
    }
  });
}

function abrirDashboard() {
  const var_strUrl = (_var_strDashboardUrl || CON_STR_DEFAULT_DASHBOARD_URL).replace(/\/+$/, "");
  chrome.tabs.create({ url: var_strUrl });
}

function setupEventListeners() {
  // Horizon Select — persiste para o overlay reutilizar
  if (elHorizonSelect) {
    elHorizonSelect.addEventListener("change", () => {
      chrome.storage.local.set({ horizonte: elHorizonSelect.value }, () => {
        if (_var_strCurrentAppId) predict();
      });
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

  if (elApiUrlInput) {
    elApiUrlInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        salvarUrlApi();
      }
    });
  }

  if (elSaveDashboardBtn) {
    elSaveDashboardBtn.addEventListener("click", salvarUrlDashboard);
  }

  if (elDashboardUrlInput) {
    elDashboardUrlInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        salvarUrlDashboard();
      }
    });
  }

  if (elOpenDashboardBtn) {
    elOpenDashboardBtn.addEventListener("click", abrirDashboard);
  }

  if (elCheckApiBtn) {
    elCheckApiBtn.addEventListener("click", verificarOuAjudarApi);
  }

  if (elStatusDot) {
    elStatusDot.addEventListener("click", verificarOuAjudarApi);
  }

  if (elCopyCmdBtn) {
    elCopyCmdBtn.addEventListener("click", copiarComandoApi);
  }

  if (elApiHelpCommand) {
    elApiHelpCommand.textContent = CON_STR_DOCKER_UP_CMD;
  }
}

function atualizarLinksDocs() {
  const var_strDocs = `${_var_strApiBaseUrl}/docs`;
  const elApiLink = document.getElementById("apiLink");
  if (elApiLink) {
    elApiLink.href = var_strDocs;
  }
  if (elApiHelpDocsLink) {
    elApiHelpDocsLink.href = var_strDocs;
  }
}

/**
 * localhost / 127.0.0.1 = Docker local. Qualquer outro host = nuvem (Render/Railway/etc).
 */
function isApiLocal() {
  try {
    const var_objUrl = new URL(_var_strApiBaseUrl);
    const var_strHost = (var_objUrl.hostname || "").toLowerCase();
    return var_strHost === "localhost" || var_strHost === "127.0.0.1" || var_strHost === "[::1]" || var_strHost === "::1";
  } catch {
    return true;
  }
}

// ── API Health Check ──
async function checkApiStatus() {
  try {
    const var_objResponse = await fetch(`${_var_strApiBaseUrl}/health`, { signal: AbortSignal.timeout(3000) });
    if (!var_objResponse.ok) throw new Error("unhealthy");
    const var_dictData = await var_objResponse.json();
    elStatusDot.classList.remove("offline");
    elStatusDot.classList.add("online");
    elStatusDot.title = `API Online • ${var_dictData.status}`;
    return true;
  } catch {
    elStatusDot.classList.remove("online");
    elStatusDot.classList.add("offline");
    elStatusDot.title = "API Offline — clique para o passo a passo";
    return false;
  }
}

/**
 * Consulta /health. Se estiver online, confirma no botão.
 * Se estiver offline, mostra o passo a passo (local vs nuvem) e copia o comando Docker.
 * O Chrome não inicia FastAPI/Docker — só explica o que fazer no computador.
 */
async function verificarOuAjudarApi() {
  if (!elCheckApiBtn || _var_boolCheckingApi) return;
  _var_boolCheckingApi = true;
  elCheckApiBtn.disabled = true;
  definirFeedbackBotao("⏳ A verificar...", null);

  try {
    const var_boolOnline = await checkApiStatus();

    if (var_boolOnline) {
      esconderAjudaApi();
      definirFeedbackBotao("✅ API online", "is-online");
      return;
    }

    const var_boolLocal = isApiLocal();
    mostrarAjudaApi(var_boolLocal);
    definirFeedbackBotao("❌ API offline", "is-offline");
    if (var_boolLocal) {
      await copiarComandoApi();
    }
  } finally {
    _var_boolCheckingApi = false;
    elCheckApiBtn.disabled = false;
  }
}

function definirFeedbackBotao(arg_strTexto, arg_strClasse) {
  if (!elCheckApiBtn) return;
  elCheckApiBtn.textContent = arg_strTexto;
  elCheckApiBtn.classList.remove("is-online", "is-offline");
  if (arg_strClasse) elCheckApiBtn.classList.add(arg_strClasse);

  if (_var_intBtnFeedbackTimer) clearTimeout(_var_intBtnFeedbackTimer);
  _var_intBtnFeedbackTimer = null;
  if (arg_strClasse === "is-online" || arg_strClasse === "is-offline") {
    _var_intBtnFeedbackTimer = setTimeout(() => {
      elCheckApiBtn.textContent = CON_STR_BTN_CHECK_LABEL;
      elCheckApiBtn.classList.remove("is-online", "is-offline");
    }, 2000);
  }
}

function mostrarAjudaApi(arg_boolLocal) {
  if (!elApiHelpPanel) return;
  elApiHelpPanel.style.display = "block";

  if (elApiHelpLead) {
    elApiHelpLead.textContent = arg_boolLocal
      ? "O Chrome não liga o Docker. A API local está offline — siga no computador:"
      : "Serviço na nuvem offline ou a acordar. O Chrome não liga o Docker da sua máquina.";
  }

  if (elApiHelpStepsLocal) {
    elApiHelpStepsLocal.style.display = arg_boolLocal ? "block" : "none";
  }
  if (elApiHelpStepsRemote) {
    elApiHelpStepsRemote.style.display = arg_boolLocal ? "none" : "block";
  }
  if (elApiHelpNote) {
    elApiHelpNote.textContent = arg_boolLocal
      ? "O overlay na página da Steam só funciona com a API a correr. A primeira subida é lenta (~1,5 GB de modelos)."
      : "O overlay na Steam precisa da API a responder. Se o contentor ainda estiver a baixar os modelos, espere e verifique de novo.";
  }
}

function esconderAjudaApi() {
  if (elApiHelpPanel) elApiHelpPanel.style.display = "none";
}

async function copiarComandoApi() {
  const var_strCmd = CON_STR_DOCKER_UP_CMD;
  let var_boolOk = false;
  try {
    await navigator.clipboard.writeText(var_strCmd);
    var_boolOk = true;
  } catch {
    const elTmp = document.createElement("textarea");
    elTmp.value = var_strCmd;
    elTmp.setAttribute("readonly", "");
    elTmp.style.position = "fixed";
    elTmp.style.left = "-9999px";
    document.body.appendChild(elTmp);
    elTmp.select();
    try {
      var_boolOk = document.execCommand("copy");
    } catch {
      var_boolOk = false;
    }
    document.body.removeChild(elTmp);
  }

  if (elCopyCmdBtn) {
    elCopyCmdBtn.textContent = var_boolOk ? "✅ Copiado!" : "❌ Falhou copiar";
    setTimeout(() => {
      elCopyCmdBtn.textContent = "📋 Copiar comando";
    }, 1500);
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

  // Limpa avisos anteriores
  document.querySelectorAll(".api-warning").forEach(w => w.remove());
  const var_listWarnings = arg_dictData.warnings || [];
  if (var_listWarnings.length > 0) {
    const elWarningsContainer = document.createElement("div");
    elWarningsContainer.className = "api-warning";
    elWarningsContainer.style.backgroundColor = "var(--color-bg-alt)";
    elWarningsContainer.style.border = "1px solid var(--color-accent)";
    elWarningsContainer.style.color = "var(--color-accent)";
    elWarningsContainer.style.padding = "10px";
    elWarningsContainer.style.marginBottom = "15px";
    elWarningsContainer.style.borderRadius = "8px";
    elWarningsContainer.style.fontSize = "0.9rem";
    var_listWarnings.forEach(w => {
      const p = document.createElement("p");
      p.style.margin = "5px 0";
      p.textContent = `⚠️ ${w}`;
      elWarningsContainer.appendChild(p);
    });
    elResults.insertBefore(elWarningsContainer, elResults.firstChild);
  }

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

  const elGameRelease = document.getElementById("gameRelease");
  if (var_dictGame.release_date) {
    elGameRelease.textContent = `📅 Lançamento: ${var_dictGame.release_date}`;
  } else {
    elGameRelease.textContent = "";
  }

  const var_floatPrice = var_dictGame.price || 0;
  if (var_dictGame.is_coming_soon) {
    document.getElementById("gamePrice").textContent = "Não Lançado";
  } else {
    document.getElementById("gamePrice").textContent =
      var_floatPrice > 0 ? `R$ ${var_floatPrice.toFixed(2)}` : "Gratuito";
  }

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

    const elSaleHistorico = document.getElementById("saleHistorico");
    const var_dictHistoricoDesconto = arg_dictData.historico_desconto;
    if (var_dictHistoricoDesconto) {
      elSaleHistorico.textContent = var_dictHistoricoDesconto.eh_maior_historico
        ? `🏆 Maior desconto já registrado nos últimos ${var_dictHistoricoDesconto.janela_anos} anos!`
        : `📊 Maior desconto histórico: ${var_dictHistoricoDesconto.maior_desconto_pct}% em ${var_dictHistoricoDesconto.data_maior_desconto} (últimos ${var_dictHistoricoDesconto.janela_anos} anos)`;
      elSaleHistorico.style.display = "block";
    } else {
      elSaleHistorico.style.display = "none";
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

    // Probabilities — chips compactos numa linha só (em vez de 3 barras empilhadas)
    const elProbContainer = document.getElementById("probabilities");
    elProbContainer.replaceChildren();

    const var_dictProbIcons = { cai: "📉", mantem: "➡️", sobe: "📈" };

    if (var_dictClassificacao.probabilidades) {
      Object.entries(var_dictClassificacao.probabilidades).forEach(([var_strLabel, var_floatProb]) => {
        const var_intPctProb = Math.round(var_floatProb * 100);
        const elChip = document.createElement("span");
        elChip.className = `prob-chip ${var_strLabel}`;
        const elIcon = document.createElement("span");
        elIcon.className = "prob-icon";
        elIcon.textContent = var_dictProbIcons[var_strLabel] || "•";
        const elValue = document.createElement("span");
        elValue.textContent = `${var_intPctProb}%`;
        elChip.appendChild(elIcon);
        elChip.appendChild(elValue);
        elProbContainer.appendChild(elChip);
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
      const var_floatMargem = var_dictRegressao.desconto_margem_erro || 0.0;
      document.getElementById("regDiscount").textContent = `${var_dictRegressao.desconto_previsto_pct}% OFF (± ${var_floatMargem}%)`;
      
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
