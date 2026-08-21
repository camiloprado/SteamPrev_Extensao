/**
 * Previsor Steam — Content script da loja
 * Injeta um widget flutuante em store.steampowered.com/app/...
 * A previsão é pedida ao service worker (evita mixed content).
 */

const CON_STR_HOST_ID = "steamprev-overlay-host";
const CON_STR_APP_ID_RE = /\/app\/(\d+)/;
// Aviso compacto: o painel 🔌 completo fica no popup (ícone da barra do navegador).
const CON_STR_API_NOTICE =
  "Para ligar ou verificar a API, clique no ícone da extensão na barra superior do navegador.";
const CON_STR_PILL_API_HINT = "API: ícone da extensão";

let _var_strCurrentAppId = null;
let _var_strClosedAppId = null;
let _var_boolCollapsed = false;
let _var_objShadow = null;
let _var_elRoot = null;

const _var_objEls = {};

document.addEventListener("DOMContentLoaded", iniciarOverlay);
if (document.readyState !== "loading") iniciarOverlay();

function iniciarOverlay() {
  if (document.getElementById(CON_STR_HOST_ID)) return;

  chrome.storage.local.get(["theme", "overlayCollapsed"], (result) => {
    _var_boolCollapsed = Boolean(result.overlayCollapsed);
    criarHost(result.theme || null);
    observarNavegacao();
    verificarNavegacao();
  });

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "local") return;
    if (changes.theme) aplicarTema(changes.theme.newValue || null);
    if (changes.overlayCollapsed) {
      _var_boolCollapsed = Boolean(changes.overlayCollapsed.newValue);
      atualizarModoExibicao();
    }
    if (changes.horizonte && _var_strCurrentAppId && !_var_strClosedAppId) {
      solicitarPrevisao(_var_strCurrentAppId);
    }
  });
}

function criarHost(arg_strTema) {
  const elHost = document.createElement("div");
  elHost.id = CON_STR_HOST_ID;
  elHost.style.cssText = [
    "all: initial",
    "position: fixed",
    "bottom: 20px",
    "right: 20px",
    "z-index: 2147483646",
    "width: auto",
    "height: auto",
  ].join(";");

  _var_objShadow = elHost.attachShadow({ mode: "open" });

  const elLink = document.createElement("link");
  elLink.rel = "stylesheet";
  elLink.href = chrome.runtime.getURL("overlay.css");
  _var_objShadow.appendChild(elLink);

  _var_elRoot = document.createElement("div");
  _var_elRoot.className = "sp-root sp-hidden";
  _var_elRoot.innerHTML = `
    <button type="button" class="sp-pill sp-hidden" id="spPill" title="Expandir Previsor Steam">
      <span class="sp-pill-icon" id="spPillIcon">🎮</span>
      <span class="sp-pill-text" id="spPillText">Previsor Steam</span>
      <span class="sp-pill-meta" id="spPillMeta"></span>
    </button>
    <div class="sp-panel sp-hidden" id="spPanel">
      <div class="sp-header">
        <span class="sp-header-logo">🎮</span>
        <span class="sp-header-title">Previsor Steam</span>
        <div class="sp-header-actions">
          <button type="button" class="sp-icon-btn" id="spDashboard" title="Abrir dashboard Streamlit">📊</button>
          <button type="button" class="sp-icon-btn" id="spMinimize" title="Minimizar">–</button>
          <button type="button" class="sp-icon-btn" id="spClose" title="Fechar nesta página">✕</button>
        </div>
      </div>
      <div class="sp-body">
        <div class="sp-api-notice sp-hidden" id="spApiNotice"></div>
        <div class="sp-loading" id="spLoading">
          <div class="sp-spinner"></div>
          <span>Analisando dados...</span>
        </div>
        <div class="sp-error sp-hidden" id="spError"></div>
        <div id="spResults" class="sp-hidden"></div>
      </div>
    </div>
  `;
  _var_objShadow.appendChild(_var_elRoot);

  _var_objEls.pill = _var_objShadow.getElementById("spPill");
  _var_objEls.pillIcon = _var_objShadow.getElementById("spPillIcon");
  _var_objEls.pillText = _var_objShadow.getElementById("spPillText");
  _var_objEls.pillMeta = _var_objShadow.getElementById("spPillMeta");
  _var_objEls.panel = _var_objShadow.getElementById("spPanel");
  _var_objEls.apiNotice = _var_objShadow.getElementById("spApiNotice");
  _var_objEls.loading = _var_objShadow.getElementById("spLoading");
  _var_objEls.error = _var_objShadow.getElementById("spError");
  _var_objEls.results = _var_objShadow.getElementById("spResults");

  _var_objEls.apiNotice.textContent = CON_STR_API_NOTICE;

  _var_objEls.pill.addEventListener("click", () => definirColapsado(false));
  _var_objShadow.getElementById("spDashboard").addEventListener("click", abrirDashboard);
  _var_objShadow.getElementById("spMinimize").addEventListener("click", () => definirColapsado(true));
  _var_objShadow.getElementById("spClose").addEventListener("click", fecharNestaPagina);

  aplicarTema(arg_strTema);
  document.documentElement.appendChild(elHost);
}

function temaDoSistema() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function aplicarTema(arg_strTema) {
  if (!_var_elRoot) return;
  _var_elRoot.setAttribute("data-theme", arg_strTema || temaDoSistema());
}

function extrairAppId(arg_strUrl) {
  if (!arg_strUrl || !arg_strUrl.includes("store.steampowered.com")) return null;
  const var_objMatch = arg_strUrl.match(CON_STR_APP_ID_RE);
  return var_objMatch ? var_objMatch[1] : null;
}

function observarNavegacao() {
  let var_strUltimaUrl = location.href;
  const verificar = () => {
    if (location.href !== var_strUltimaUrl) {
      var_strUltimaUrl = location.href;
      verificarNavegacao();
    }
  };

  window.addEventListener("popstate", verificar);
  setInterval(verificar, 800);

  const var_objObserver = new MutationObserver(verificar);
  var_objObserver.observe(document.documentElement, { subtree: true, childList: true });
}

function verificarNavegacao() {
  const var_strAppId = extrairAppId(location.href);
  if (var_strAppId === _var_strCurrentAppId) return;

  _var_strCurrentAppId = var_strAppId;

  if (!var_strAppId) {
    esconderWidget();
    return;
  }

  if (_var_strClosedAppId && _var_strClosedAppId !== var_strAppId) {
    _var_strClosedAppId = null;
  }

  if (_var_strClosedAppId === var_strAppId) {
    esconderWidget();
    return;
  }

  mostrarWidget();
  solicitarPrevisao(var_strAppId);
}

function mostrarWidget() {
  if (!_var_elRoot) return;
  _var_elRoot.classList.remove("sp-hidden");
  atualizarModoExibicao();
}

function esconderWidget() {
  if (!_var_elRoot) return;
  _var_elRoot.classList.add("sp-hidden");
}

function atualizarModoExibicao() {
  if (!_var_elRoot || _var_elRoot.classList.contains("sp-hidden")) return;
  _var_objEls.pill.classList.toggle("sp-hidden", !_var_boolCollapsed);
  _var_objEls.panel.classList.toggle("sp-hidden", _var_boolCollapsed);
}

function definirColapsado(arg_boolValor) {
  _var_boolCollapsed = arg_boolValor;
  chrome.storage.local.set({ overlayCollapsed: arg_boolValor });
  atualizarModoExibicao();
}

function fecharNestaPagina() {
  _var_strClosedAppId = _var_strCurrentAppId;
  esconderWidget();
}

function abrirDashboard() {
  chrome.runtime.sendMessage({ type: "OPEN_DASHBOARD" }, () => {
    void chrome.runtime.lastError;
  });
}

function definirAvisoApi(arg_boolVisivel) {
  _var_objEls.apiNotice.classList.toggle("sp-hidden", !arg_boolVisivel);
}

function mostrarLoading() {
  definirAvisoApi(false);
  _var_objEls.loading.classList.remove("sp-hidden");
  _var_objEls.error.classList.add("sp-hidden");
  _var_objEls.results.classList.add("sp-hidden");
  _var_objEls.pillText.textContent = "Analisando...";
  _var_objEls.pillMeta.textContent = "";
  _var_objEls.pillIcon.textContent = "🎮";
}

function mostrarErro(arg_strMsg) {
  definirAvisoApi(true);
  _var_objEls.loading.classList.add("sp-hidden");
  _var_objEls.results.classList.add("sp-hidden");
  _var_objEls.error.classList.remove("sp-hidden");
  _var_objEls.error.replaceChildren();

  const elMsg = document.createElement("span");
  elMsg.textContent = arg_strMsg;
  _var_objEls.error.appendChild(elMsg);

  _var_objEls.pillText.textContent = CON_STR_PILL_API_HINT;
  _var_objEls.pillMeta.textContent = "";
  _var_objEls.pillIcon.textContent = "⚠️";
}

function solicitarPrevisao(arg_strAppId) {
  mostrarLoading();
  chrome.runtime.sendMessage({ type: "PREDICT", appId: arg_strAppId }, (response) => {
    if (arg_strAppId !== _var_strCurrentAppId) return;
    if (chrome.runtime.lastError) {
      mostrarErro("Extensão indisponível. Recarregue a página.");
      return;
    }
    if (!response || !response.ok) {
      mostrarErro((response && response.error) || "Não foi possível conectar à API");
      return;
    }
    renderizarResultados(response.data);
  });
}

function textoPreco(arg_dictGame) {
  if (arg_dictGame.is_coming_soon) return "Não Lançado";
  const var_floatPrice = arg_dictGame.price || 0;
  return var_floatPrice > 0 ? `R$ ${var_floatPrice.toFixed(2)}` : "Gratuito";
}

function renderizarResultados(arg_dictData) {
  definirAvisoApi(false);
  _var_objEls.loading.classList.add("sp-hidden");
  _var_objEls.error.classList.add("sp-hidden");
  _var_objEls.results.classList.remove("sp-hidden");
  _var_objEls.results.replaceChildren();

  const var_dictGame = arg_dictData.game || {};
  const var_dictClassificacao = arg_dictData.classificacao;
  const var_dictRegressao = arg_dictData.regressao;
  const var_listWarnings = arg_dictData.warnings || [];

  var_listWarnings.forEach((w) => {
    const elWarn = document.createElement("div");
    elWarn.className = "sp-warning";
    elWarn.textContent = `⚠️ ${w}`;
    _var_objEls.results.appendChild(elWarn);
  });

  const elGame = document.createElement("div");
  elGame.className = "sp-game";
  if (var_dictGame.header_image) {
    const elImg = document.createElement("img");
    elImg.src = var_dictGame.header_image;
    elImg.alt = "";
    elGame.appendChild(elImg);
  }
  const elInfo = document.createElement("div");
  elInfo.className = "sp-game-info";
  const elName = document.createElement("div");
  elName.className = "sp-game-name";
  elName.textContent = var_dictGame.name || "Jogo";
  const elMeta = document.createElement("div");
  elMeta.className = "sp-meta";
  const elPrice = document.createElement("span");
  elPrice.className = "sp-badge";
  elPrice.textContent = textoPreco(var_dictGame);
  elMeta.appendChild(elPrice);
  if (var_dictGame.review_score) {
    const elReview = document.createElement("span");
    elReview.className = "sp-badge sp-badge-outline";
    elReview.textContent = `⭐ ${var_dictGame.review_score}%`;
    elMeta.appendChild(elReview);
  }
  elInfo.appendChild(elName);
  elInfo.appendChild(elMeta);
  elGame.appendChild(elInfo);
  _var_objEls.results.appendChild(elGame);

  const var_dictClassIcons = { cai: "📉", mantem: "➡️", sobe: "📈" };

  if (var_dictGame.is_on_sale) {
    const elSale = criarCard("🎉 Desconto ativo", `${var_dictGame.discount_percent}% OFF`);
    elSale.classList.add("sp-sale");
    const elDesc = document.createElement("div");
    elDesc.className = "sp-card-desc";
    elDesc.textContent = var_dictGame.sale_end_date
      ? `Término estimado: ${var_dictGame.sale_end_date}`
      : "Predição abortada: o jogo já está em promoção.";
    elSale.appendChild(elDesc);
    _var_objEls.results.appendChild(elSale);

    _var_objEls.pillIcon.textContent = "🎉";
    _var_objEls.pillText.textContent = var_dictGame.name || "Em promoção";
    _var_objEls.pillMeta.textContent = `${var_dictGame.discount_percent}%`;
    return;
  }

  if (var_dictClassificacao) {
    const elClass = criarCard(
      "Direção do preço",
      var_dictClassificacao.classe_emoji || var_dictClassificacao.classe
    );
    const elConf = document.createElement("div");
    elConf.className = "sp-confidence";
    const elBar = document.createElement("div");
    elBar.className = "sp-bar";
    const elFill = document.createElement("div");
    elFill.className = "sp-bar-fill";
    const var_intPct = Math.round((var_dictClassificacao.confianca || 0) * 100);
    elFill.style.width = `${var_intPct}%`;
    elBar.appendChild(elFill);
    const elPct = document.createElement("span");
    elPct.textContent = `${var_intPct}%`;
    elConf.appendChild(elBar);
    elConf.appendChild(elPct);
    elClass.appendChild(elConf);
    _var_objEls.results.appendChild(elClass);

    _var_objEls.pillIcon.textContent = var_dictClassIcons[var_dictClassificacao.classe] || "🎮";
  } else {
    _var_objEls.pillIcon.textContent = "🎮";
  }

  if (var_dictRegressao) {
    const elReg = criarCard("Próxima promoção", `${var_dictRegressao.dias_estimados} dias`, true);
    if (var_dictRegressao.descricao) {
      const elDesc = document.createElement("div");
      elDesc.className = "sp-card-desc";
      elDesc.textContent = var_dictRegressao.descricao;
      elReg.appendChild(elDesc);
    }
    if (var_dictRegressao.desconto_previsto_pct > 0) {
      const elExtra = document.createElement("div");
      elExtra.className = "sp-card-desc";
      const var_floatMargem = var_dictRegressao.desconto_margem_erro || 0;
      const var_floatPreco = var_dictRegressao.preco_estimado;
      const var_strPreco = var_floatPreco > 0 ? `R$ ${var_floatPreco.toFixed(2)}` : "Gratuito";
      elExtra.textContent = `Desconto ~${var_dictRegressao.desconto_previsto_pct}% (± ${var_floatMargem}%) · ${var_strPreco}`;
      elReg.appendChild(elExtra);
    }
    _var_objEls.results.appendChild(elReg);
    _var_objEls.pillMeta.textContent = `${var_dictRegressao.dias_estimados}d`;
  } else {
    _var_objEls.pillMeta.textContent = "";
  }

  _var_objEls.pillText.textContent = var_dictGame.name || "Previsor Steam";
}

function criarCard(arg_strLabel, arg_strValue, arg_boolDays) {
  const elCard = document.createElement("div");
  elCard.className = "sp-card";
  const elLabel = document.createElement("div");
  elLabel.className = "sp-card-label";
  elLabel.textContent = arg_strLabel;
  const elValue = document.createElement("div");
  elValue.className = arg_boolDays ? "sp-card-value sp-days" : "sp-card-value";
  elValue.textContent = arg_strValue;
  elCard.appendChild(elLabel);
  elCard.appendChild(elValue);
  return elCard;
}
