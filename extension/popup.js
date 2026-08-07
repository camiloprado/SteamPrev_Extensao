/**
 * Previsor Steam — Chrome Extension Popup Logic
 */

const API_BASE_URL = "http://localhost:8000";

// ── DOM Elements ──
const searchInput = document.getElementById("searchInput");
const searchBtn = document.getElementById("searchBtn");
const statusDot = document.getElementById("statusDot");
const loading = document.getElementById("loading");
const results = document.getElementById("results");
const error = document.getElementById("error");
const errorMsg = document.getElementById("errorMsg");
const quickGames = document.getElementById("quickGames");

// ── Init ──
document.addEventListener("DOMContentLoaded", () => {
  checkApiStatus();
  setupEventListeners();
});

function setupEventListeners() {
  // Search button
  searchBtn.addEventListener("click", () => predict(searchInput.value));

  // Enter key
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") predict(searchInput.value);
  });

  // Quick game chips
  quickGames.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const query = chip.dataset.query;
      searchInput.value = query;
      predict(query);
    });
  });
}

// ── API Health Check ──
async function checkApiStatus() {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, { signal: AbortSignal.timeout(3000) });
    const data = await res.json();
    statusDot.classList.remove("offline");
    statusDot.classList.add("online");
    statusDot.title = `API Online • ${data.status}`;
  } catch {
    statusDot.classList.remove("online");
    statusDot.classList.add("offline");
    statusDot.title = "API Offline";
  }
}

// ── Predict ──
async function predict(query) {
  if (!query || !query.trim()) {
    showError("Digite o nome de um jogo ou AppID");
    return;
  }

  showLoading();

  try {
    const res = await fetch(`${API_BASE_URL}/predict/game`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query.trim() }),
      signal: AbortSignal.timeout(15000),
    });

    if (res.status === 404) {
      showError(`Jogo não encontrado: "${query}"`);
      return;
    }

    if (!res.ok) {
      showError(`Erro na API (${res.status})`);
      return;
    }

    const data = await res.json();
    showResults(data);
  } catch (err) {
    if (err.name === "AbortError" || err.name === "TimeoutError") {
      showError("Timeout: a API demorou para responder");
    } else {
      showError("Não foi possível conectar à API");
    }
  }
}

// ── Show Results ──
function showResults(data) {
  hideAll();
  results.style.display = "block";

  const game = data.game || {};
  const clf = data.classificacao;
  const reg = data.regressao;

  // Game info
  document.getElementById("gameName").textContent = game.name || "Jogo";

  const gameImage = document.getElementById("gameImage");
  if (game.header_image) {
    gameImage.src = game.header_image;
    gameImage.style.display = "block";
  } else {
    gameImage.style.display = "none";
  }

  const price = game.price || 0;
  document.getElementById("gamePrice").textContent =
    price > 0 ? `R$ ${price.toFixed(2)}` : "Gratuito";

  document.getElementById("gameReview").textContent =
    game.review_score ? `⭐ ${game.review_score}%` : "N/A";

  // Classification
  const classCard = document.getElementById("classCard");
  if (clf) {
    classCard.style.display = "block";

    const classIcons = { cai: "📉", mantem: "➡️", sobe: "📈" };
    document.getElementById("classIcon").textContent = classIcons[clf.classe] || "📊";
    document.getElementById("classValue").textContent = clf.classe_emoji || clf.classe;

    // Confidence bar
    const pct = Math.round(clf.confianca * 100);
    document.getElementById("confidenceBar").style.width = `${pct}%`;
    document.getElementById("confidenceValue").textContent = `${pct}%`;

    // Probabilities
    const probContainer = document.getElementById("probabilities");
    probContainer.innerHTML = "";

    const probColors = { cai: "cai", mantem: "mantem", sobe: "sobe" };

    if (clf.probabilidades) {
      Object.entries(clf.probabilidades).forEach(([label, prob]) => {
        const pctProb = Math.round(prob * 100);
        probContainer.innerHTML += `
          <div class="prob-row">
            <span class="prob-label">${label}</span>
            <div class="prob-bar-container">
              <div class="prob-bar ${probColors[label] || ''}" style="width: ${pctProb}%"></div>
            </div>
            <span class="prob-value">${pctProb}%</span>
          </div>
        `;
      });
    }
  } else {
    classCard.style.display = "none";
  }

  // Regression
  const regCard = document.getElementById("regCard");
  if (reg) {
    regCard.style.display = "block";
    document.getElementById("regValue").textContent = `${reg.dias_estimados} dias`;
    document.getElementById("regDesc").textContent = reg.descricao;
  } else {
    regCard.style.display = "none";
  }
}

// ── UI Helpers ──
function showLoading() {
  hideAll();
  loading.style.display = "flex";
}

function showError(msg) {
  hideAll();
  error.style.display = "flex";
  errorMsg.textContent = msg;
}

function hideAll() {
  loading.style.display = "none";
  results.style.display = "none";
  error.style.display = "none";
}
