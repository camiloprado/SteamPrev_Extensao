# Deploy no Render — passo a passo

Este guia sobe a **API FastAPI** e o **dashboard Streamlit** no [Render](https://render.com) para que a extensão Chrome funcione **sem ligar nada na sua máquina**.

Você vai terminar com duas URLs HTTPS, por exemplo:

- API: `https://steamprev-api.onrender.com`
- Dashboard: `https://steamprev-dashboard.onrender.com`

Cole a primeira na extensão (⚙️ → URL da API) e a segunda em **URL do Dashboard Streamlit**. O botão **📊 Abrir dashboard** no rodapé do popup abre o Streamlit numa nova aba.

O bot Discord **não** entra neste deploy (é um processo contínuo à parte; veja a nota no final).

---

## Antes de começar — leia isto

1. **Crie uma conta** em [render.com](https://render.com) (login com GitHub é o mais simples) e deixe este repositório no GitHub (público ou privado).
2. **Plano da API (RAM):** os modelos de classificação somam cerca de **1,5 GB em disco** e a API pré-carrega os 4 horizontes na memória. **Não use Free nem Starter (512 MB) na API** — o serviço costuma morrer (OOM). Use **Standard (2 GB)** no mínimo; se o deploy falhar por memória, suba para **Pro (4 GB)**.
3. **Plano Free (aviso):** Web Services gratuitos **desligam após 15 minutos sem tráfego**. O próximo clique espera ~1 minuto (às vezes mais) enquanto o container acorda **e baixa de novo os modelos** (o disco do Free é efêmero). Além disso, o workspace tem **750 horas/mês** — dois serviços Free 24h estouram o limite. Para uso real da extensão, deixe a **API sempre ligada** (Starter/Standard/Pro).
4. **Primeiro arranque é lento:** na primeira subida a API baixa os `.joblib` do [GitHub Releases](https://github.com/camiloprado/SteamPrev_Machine_Learning/releases/latest) (`MODELS_BASE_URL`). Pode levar vários minutos. Acompanhe os **Logs**.
5. Tenha à mão (opcional, mas recomendado) a chave **ITAD**. Sem ela a API ainda responde, porém o histórico de preços fica limitado/simulado. **Não cole chaves neste repositório.**

---

## Caminho A — Blueprint (`render.yaml`) — recomendado

O arquivo `render.yaml` na raiz do repo já descreve os dois Web Services, os Dockerfiles e as variáveis (sem segredos).

1. Faça push deste repositório para o GitHub.
2. No Render: **Dashboard → New → Blueprint**.
3. Conecte o repositório `SteamPrev_Extensao` (autorize o GitHub se pedir).
4. Confirme o Blueprint. O Render cria:
   - `steamprev-api` (Docker `api/Dockerfile`, health `/health`, plano **Standard**)
   - `steamprev-dashboard` (Docker `dashboard/Dockerfile`, health `/_stcore/health`, plano **Starter**)
5. Quando pedir valores `sync: false`, cole:
   - **ITAD_API_KEY** — chave da [IsThereAnyDeal](https://isthereanydeal.com) (pode deixar vazio e preencher depois em Environment).
   - **STEAM_API_KEY** — opcional (a loja pública da Steam já é consultada sem chave).
6. Clique em **Apply**. Espere o build Docker + o primeiro start da API (download dos modelos).
7. Quando ambos estiverem **Live**, copie as URLs públicas (botão da extensão do navegador ao lado do nome do serviço, ou **Settings → Connect**).
8. Vá para a secção [Depois do deploy — configurar a extensão](#depois-do-deploy--configurar-a-extensão).

Valores que o Blueprint já define (não invente outros nomes):

| Serviço | Variável | Valor |
|---|---|---|
| API | `PORT` | `8000` (tem de coincidir com o `CMD` do Dockerfile) |
| API | `MODELS_PATH` | `resources/models` |
| API | `MODELS_BASE_URL` | `https://github.com/camiloprado/SteamPrev_Machine_Learning/releases/latest/download` |
| Dashboard | `PORT` | `8501` |
| Dashboard | `API_BASE_URL` | `http://steamprev-api:8000` (rede interna do Render; o Streamlit fala com a API **no servidor**, não no browser) |

**Não defina `CORS_ORIGINS`** a menos que saiba o que está a fazer. O padrão da API já aceita `chrome-extension://…` (popup) e `http://localhost:…`. Se você preencher `CORS_ORIGINS`, esse padrão é **substituído** e o popup pode deixar de conseguir chamar a API.

---

## Caminho B — dois Web Services à mão

Use isto se preferir o botão **New → Web Service** em vez do Blueprint.

### B.1 — API FastAPI

1. **New → Web Service** → ligue o mesmo repositório GitHub.
2. Preencha:

   | Campo | Valor a copiar |
   |---|---|
   | Name | `steamprev-api` |
   | Language / Runtime | **Docker** |
   | Root Directory | *(vazio — raiz do repo)* |
   | Dockerfile Path | `api/Dockerfile` |
   | Docker Build Context Directory | `.` *(raiz do repo; o Dockerfile faz `COPY api/`, `COPY core/`, `COPY scripts/`)* |
   | Instance type | **Standard** (2 GB). Não escolha Free. |
   | Health Check Path | `/health` |

3. **Environment** (Environment Variables):

   ```
   PORT=8000
   MODELS_PATH=resources/models
   MODELS_BASE_URL=https://github.com/camiloprado/SteamPrev_Machine_Learning/releases/latest/download
   ITAD_API_KEY=cole_sua_chave_aqui
   STEAM_API_KEY=
   ```

   Deixe `STEAM_API_KEY` vazio se não tiver. Não commite estas chaves.

4. **Create Web Service** e espere ficar **Live**. Teste no browser:

   ```
   https://steamprev-api.onrender.com/health
   ```

   Resposta esperada: JSON com `"status": "healthy"` (ou `"degraded"` se algum modelo falhou). Também pode abrir `/docs` (Swagger).

### B.2 — Dashboard Streamlit

1. **New → Web Service** → o **mesmo** repositório.
2. Preencha:

   | Campo | Valor a copiar |
   |---|---|
   | Name | `steamprev-dashboard` |
   | Runtime | **Docker** |
   | Dockerfile Path | `dashboard/Dockerfile` |
   | Docker Build Context Directory | `.` |
   | Instance type | **Starter** chega (Streamlit é mais leve). Free funciona, mas dorme aos 15 min. |
   | Health Check Path | `/_stcore/health` |

3. **Environment:**

   ```
   PORT=8501
   API_BASE_URL=http://steamprev-api:8000
   ITAD_API_KEY=cole_sua_chave_aqui
   ```

   `API_BASE_URL` usa o **nome do serviço da API** na rede privada do Render (`steamprev-api`) e a porta interna `8000`. Se o nome do Web Service da API for outro, troque só essa parte.

   Alternativa (pública, mais lenta): `API_BASE_URL=https://steamprev-api.onrender.com`

4. **Create Web Service**. Quando estiver Live, abra a URL `https://steamprev-dashboard.onrender.com` e confirme que a página **Previsão** consulta jogos.

---

## Como os modelos chegam ao servidor

Os `.joblib` **não** estão no Git (são grandes e estão no `.gitignore`).

No arranque, `api/models_loader.py` chama `scripts/download_models.py`, que baixa a release mais recente de:

```
https://github.com/camiloprado/SteamPrev_Machine_Learning/releases/latest/download
```

Isso só funciona no Docker se a imagem incluir a pasta `scripts/` (o `api/Dockerfile` já faz `COPY scripts/ ./scripts/`).

Na prática, nos **Logs** da API você deve ver linhas como `VERIFICAÇÃO DE MODELOS ML` e `📥 Downloading …`. Sem isso, a API sobe “vazia” e `/health` fica `unhealthy`.

No plano Free, **cada despertar** pode repetir o download (disco efémero). Mais um motivo para não usar Free na API.

---

## Depois do deploy — configurar a extensão

A extensão **não** adivinha as URLs do Render. Você cola uma vez nas configurações.

1. Chrome / Opera / Brave → `chrome://extensions` (ou `opera://extensions` / `brave://extensions`).
2. Ative **Modo do desenvolvedor**.
3. **Carregar sem compactação** → escolha a pasta `extension/` deste projeto.
4. Clique no ícone da extensão → ⚙️.
5. **URL da API:** cole `https://steamprev-api.onrender.com` (sem barra no final) → **Salvar** (ou Enter).
6. **URL do Dashboard Streamlit:** cole `https://steamprev-dashboard.onrender.com` → **Salvar** (ou Enter).
7. O ponto no canto do popup deve ficar **verde** (API online). Se estiver vermelho, a API ainda está a acordar ou a URL está errada.
8. Abra qualquer jogo em `https://store.steampowered.com/app/...` — o overlay e o popup passam a usar a API HTTPS. O overlay **não** fala com localhost a partir da página da Steam; o *service worker* já faz o proxy, e com a URL HTTPS do Render isso também funciona.
9. Clique em **📊 Abrir dashboard** no rodapé do popup (ou no 📊 do overlay) para abrir o Streamlit numa nova aba.

A extensão já tem `host_permissions` para `https://*/*`, portanto a URL `*.onrender.com` não exige alterar o `manifest.json`.

---

## Checklist rápido (leigo)

- [ ] Conta no Render + repo no GitHub
- [ ] Dois Web Services: API (`api/Dockerfile`) e Dashboard (`dashboard/Dockerfile`)
- [ ] `PORT=8000` na API e `PORT=8501` no dashboard
- [ ] API em **Standard (2 GB)** ou maior — não Free
- [ ] `ITAD_API_KEY` colada no Environment da API (e do dashboard, se quiser a página Histórico)
- [ ] `/health` da API responde `healthy`
- [ ] URLs HTTPS coladas na ⚙️ da extensão
- [ ] Extensão recarregada em `chrome://extensions`

---

## Problemas frequentes

**Deploy da API falha / reinicia em loop**  
Quase sempre **falta de RAM**. Suba o plano para Standard ou Pro. Confira Logs por `Killed` ou OOM.

**`/health` demora ou falha no primeiro deploy**  
Ainda está a baixar ~1,5 GB de modelos. Espere e leia os Logs. Não apague o serviço no meio do download.

**Popup: “Não foi possível conectar à API”**  
URL sem `https://`, barra a mais, ou serviço Free a acordar. Espere 1–2 minutos e teste `/health` no browser.

**Dashboard não prevê nada**  
`API_BASE_URL` errado. Tem de apontar para a API (interno `http://steamprev-api:8000` ou a URL pública `https://…onrender.com`). A sidebar da página inicial do Streamlit também deixa mudar a URL.

**Plano Free “funciona uma vez e depois some”**  
É o spin-down de 15 minutos. A API precisa baixar os modelos de novo. Mude a API para um plano pago.

**CORS**  
Deixe `CORS_ORIGINS` vazio. O popup roda como `chrome-extension://…`, já permitido por omissão. O dashboard chama a API **pelo servidor Streamlit** (`httpx`), então CORS do browser não se aplica a essa chamada.

---

## Bot Discord (fora do escopo)

Não é necessário para a extensão. Se quiser no futuro: **New → Background Worker**, Dockerfile `bot_discord/Dockerfile`, contexto `.`, variáveis `API_BASE_URL` (interno ou público da API) e `DISCORD_TOKEN`. Background Workers **não têm plano Free**.
