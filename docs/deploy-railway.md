# Railway vs GitHub — o que cabe neste projeto

**Resposta curta (agosto de 2026):** a Railway **não fica grátis** para esta API, e o **GitHub não a hospeda**. O overlay da extensão precisa de um processo 24/7 com os `.joblib` carregados; isso exige RAM e disco que os planos Trial/Free da Railway cortam, e que Pages/Actions/Codespaces simplesmente não oferecem.

Se a meta é **não pagar nada**, o caminho que já funciona é o local: `docker compose up` e a extensão no default `http://localhost:8000` (⚙️). Não cole uma URL pública se o serviço estiver a dormir ou a OOM.

Não há `railway.json` neste repo de propósito — um ficheiro desses faria parecer que o deploy é gratuito. O Render continua documentado em [deploy-render.md](deploy-render.md).

---

## 1. O que este projeto realmente precisa

Medido no código e na [release `models-v2.2`](https://github.com/camiloprado/SteamPrev_Machine_Learning/releases/tag/models-v2.2) (17/18 ago 2026), não chutado.

### Disco — os `.joblib`

`scripts/download_models.py` baixa estes ficheiros no arranque (`ensure_models`). Tamanhos da release:

| Ficheiro | Tamanho |
|---|---|
| `modelo_classificacao_30d.joblib` | 394,2 MB |
| `modelo_classificacao_60d.joblib` | 373,3 MB |
| `modelo_classificacao_90d.joblib` | 304,5 MB |
| `modelo_latest.joblib` | 394,2 MB |
| `modelo_regressao_dias_{30,60,90}d.joblib` | ~4,4–4,5 MB cada |
| `modelo_regressao_desconto_{30,60,90}d.joblib` | ~4,5 MB cada |

**Soma ≈ 1,49 GB em disco** (~1,46 GiB). Confirma o “~1,5 GB” de [deploy-render.md](deploy-render.md). Os `.joblib` **não** vão no Git (`.gitignore`); a API baixa-os de `MODELS_BASE_URL`.

### RAM — tudo pré-carregado

Em `api/models_loader.py`, `load_models()` faz download e depois:

```python
for var_strHoriz in ["30d", "60d", "90d", "latest"]:
    self.ensure_models_for_horizon(var_strHoriz)
```

Os quatro horizontes ficam em dicts na memória (classificação RandomForest + regressões XGBoost). O `gc.collect()` não descarrega horizontes antigos. Só os RandomForest já são ~1,47 GB em disco; desserializados pelo sklearn costumam ocupar **pelo menos isso**, mais o runtime (Python 3.11, scikit-learn, xgboost, pandas, uvicorn).

O guia Render pede **Standard 2 GB no mínimo** e **Pro 4 GB** se OOM. Esse é o intervalo real: **~2 GB de RAM always-on**, com risco de precisar de ~3–4 GB.

### Always-on

O overlay em `store.steampowered.com` manda `PREDICT` ao service worker, que faz `POST /predict/game` com timeout de **15 s** (`extension/background.js`). A rota puxa Steam + ITAD e corre os modelos em memória (`api/routes/predict.py`).

Se o contentor dorme, o próximo clique espera o cold start **e** o re-download de ~1,5 GB. Isso estoura os 15 s. Serverless / spin-down **não serve** para esta extensão.

O dashboard Streamlit (porta 8501) é opcional — o popup só abre o link. O bot Discord não entra.

### Portas, Docker, env

| Peça | Valor |
|---|---|
| API | `api/Dockerfile` → uvicorn `0.0.0.0:8000`, health `/health` |
| Dashboard | `dashboard/Dockerfile` → Streamlit `:8501` |
| Env | `PORT`, `MODELS_PATH`, `MODELS_BASE_URL`, `ITAD_API_KEY`, `STEAM_API_KEY` |
| Não definir | `CORS_ORIGINS` (o default já aceita `chrome-extension://…`) |

A extensão **não** adivinha URLs. Default continua `http://localhost:8000` / `http://localhost:8501`. URL pública só se colar em ⚙️.

---

## 2. Railway hoje (docs oficiais)

Consultado em **21 ago 2026**:

- Planos e preços unitários: [docs.railway.com/pricing/plans](https://docs.railway.com/pricing/plans)
- Página de pricing: [railway.com/pricing](https://railway.com/pricing)
- Trial: [docs.railway.com/pricing/free-trial](https://docs.railway.com/pricing/free-trial)
- FAQ (“Hobby é grátis?”): [docs.railway.com/pricing/plans](https://docs.railway.com/pricing/plans#is-the-hobby-plan-free)
- Serverless (ex-app sleeping): [docs.railway.com/deployments/serverless](https://docs.railway.com/deployments/serverless)

### Planos e tetos por serviço

| Plano | Assinatura | Crédito de uso | RAM máx. | Disco efémero | Volume |
|---|---|---|---|---|---|
| **Trial** (30 dias) | $0 | **$5 uma vez** | **1 GB** | **1 GB** | 0,5 GB |
| **Free** (depois do trial) | $0 | **$1 / mês** | **0,5 GB** | **1 GB** | 0,5 GB |
| **Hobby** | **$5 / mês** | $5 / mês (incluídos na assinatura) | 48 GB | 100 GB | 5 GB |
| **Pro** | $20 / mês | $20 / mês | 1 TB | 100 GB | 1 TB |

O Trial dá as *features* do Hobby, mas **capado a 1 GB de RAM**. Sem verificação GitHub, o trial ainda restringe rede de saída (a API precisa de GitHub Releases + Steam + ITAD).

A FAQ oficial: *“Is the hobby plan free? **No.** […] you always pay the $5 subscription fee.”*

### Preço por recurso (além da assinatura)

| Recurso | Preço |
|---|---|
| RAM | **$10 / GB / mês** |
| CPU | $20 / vCPU / mês |
| Egress | $0,05 / GB |
| Volume | $0,15 / GB / mês |

O crédito de $5 do Hobby **não acumula** mês a mês. Uso > $5 → cobra-se a diferença. Serviços always-on cobram RAM mesmo sem tráfego.

Serverless só dorme se **ligares** a opção, após **10 min sem tráfego de saída**. O primeiro pedido pode dar **502**. Péssimo para o overlay.

---

## 3. A matemática: cabe sem fatura?

### Trial / Free — não cabe (teto, não só preço)

1. **Disco:** 1,49 GB de modelos > **1 GB** de disco efémero. O download no arranque não cabe.
2. **RAM:** ~2 GB carregados > **0,5–1 GB** de teto. OOM mesmo que o disco magicamente coubesse.
3. **Crédito:** $5 no trial ≈ **0,5 GB-mês** de RAM ($10/GB). Esta API sozinha estoura isso em dias, não em 30.

Conclusão: **não dá para “experimentar de graça” este workload** no Trial/Free. O processo morre por disco ou por RAM antes de `/health` ficar `healthy`.

### Hobby — corre, mas cobra

Só o Hobby (ou Pro) tem teto de RAM/disco suficiente.

Custo **sempre ligado**, só a API, RAM média **2 GB** (o mínimo que o Render já pede):

| Linha | Conta | ≈ / mês |
|---|---|---|
| RAM | 2 GB × $10 | **$20** |
| CPU idle | ~0,05 vCPU × $20 | ~$1 |
| Egress da extensão | baixo | cents |
| **Uso** | | **~$21** |
| Assinatura Hobby | $5, que **contam** para os primeiros $5 de uso | — |
| **Fatura** | uso $21 > crédito $5 | **~$21** |

Se a RAM real for 1,6 GB → ~$17. Se OOM e precisares de ~4 GB → **~$40+**. Dois serviços (API + Streamlit) somam RAM dos dois.

O crédito de $5 do Hobby paga **0,5 GB always-on**. Esta API precisa de ~4× isso.

**Railway gratuita / sem cartão para este projeto: não.**

---

## 4. GitHub como host — o que é real

| Produto | O que faz | Serve esta extensão? |
|---|---|---|
| **GitHub Pages** | Site **estático** (HTML/CSS/JS). Sem processo Python, sem sklearn, sem `POST` persistente. | **Não.** Não corre FastAPI nem carrega `.joblib`. |
| **GitHub Actions** | Jobs **efémeros**. Runners hospedados: **máx. 6 h** por job ([limits](https://docs.github.com/en/actions/reference/limits)). Sem URL pública 24/7. | **Não.** O overlay precisa de API contínua, não de um workflow. |
| **Codespaces** | IDE na cloud, sessão tua, fatura depois das horas grátis. | **Não** é produção nem URL estável para a Steam. |
| **GitHub Releases** | Já é usado: `MODELS_BASE_URL` aponta para a release dos modelos. | **Sim**, mas só como **armazém** dos `.joblib`. Não substitui a API. |

Não existe caminho GitHub-nativo realista: um widget estático no Pages não chama Steam+ITAD nem corre RandomForest/XGBoost. Reescrever inferência no browser seria outro projeto, não “hospedar no GitHub”.

---

## 5. O que fazer (um caminho)

### Se a meta é $0 — fica no localhost

1. `docker compose up` (API na 8000; dashboard 8501 se quiseres).
2. Extensão **sem** URL pública — o default já é localhost.
3. A máquina tem de estar ligada quando usas a Steam. É o único modo **sem fatura** que esta arquitectura permite.

### Se precisas da extensão sem PC ligado — paga RAM, só a API

O dashboard Streamlit **não** é necessário para o overlay. Um único serviço FastAPI reduz a conta.

Comparação always-on (só API, ~2 GB), preços oficiais na mesma data:

| Host | Plano | Preço típico | Nota |
|---|---|---|---|
| **Railway Hobby** | uso ~2 GB RAM | **~$17–25 / mês** | mais barato *se* a RAM média ficar perto de 2 GB |
| **Render Standard** | 2 GB fixos | **$25 / mês** ([render.com/pricing](https://render.com/pricing)) | já está no `render.yaml`; previsível |
| **Render Pro** | 4 GB | **$85 / mês** | se Standard der OOM |
| **Railway ~4 GB** | 4 × $10 | **~$40+ / mês** | mais barato que Render Pro *se* precisares de 4 GB |

Não migres cegamente Render → Railway: a Railway **também cobra**, e o Trial/Free **não aguentam** os modelos. Se o Render Standard já está Live, o movimento mais barato é **apagar o dashboard** no Render (Starter ~$7) e deixar **só a API Standard**. Trocar de plataforma não zera a fatura.

GitHub Pages/Actions **não** são plano B.

---

## 6. Receita mínima paga (só API, se aceitares a fatura)

Não faças isto à espera de $0. Serve se quiseres Railway **já a pagar Hobby** (cartão obrigatório depois do trial).

1. Conta em [railway.com](https://railway.com/) → plano **Hobby** ($5/mês + uso). Trial/Free **não**.
2. **New Project → Deploy from GitHub** → este repositório.
3. Um serviço, não dois:
   - Dockerfile: `api/Dockerfile`
   - Context: raiz do repo (o Dockerfile faz `COPY api/`, `COPY core/`, `COPY scripts/`)
4. Variáveis (sem commitar segredos):

   ```
   PORT=8000
   MODELS_PATH=resources/models
   MODELS_BASE_URL=https://github.com/camiloprado/SteamPrev_Machine_Learning/releases/latest/download
   ITAD_API_KEY=cole_sua_chave_aqui
   STEAM_API_KEY=
   ```

   `PORT=8000` tem de coincidir com o `CMD` do Dockerfile (`--port 8000`). A Railway injecta `PORT`; se não fixares 8000, o processo escuta 8000 e o proxy da Railway aponta para outra porta. Em **Settings → Networking**, target port **8000** e gera o domínio `*.up.railway.app`.
5. Healthcheck HTTP: `/health`. O primeiro start **baixa ~1,5 GB** — aumenta o timeout do healthcheck (vários minutos) senão o deploy é morto a meio do download.
6. **Não** actives Serverless.
7. Replica limits: memória **≥ 2 GB** (4 GB se OOM). Sem limite, a Railway escala e **cobre a RAM real** ($10/GB/mês).
8. Quando `/health` devolver `"status": "healthy"`, cola `https://….up.railway.app` em ⚙️ → **URL da API**. Deixa o dashboard no localhost ou vazio.
9. Põe um **usage limit** no workspace ([cost control](https://docs.railway.com/pricing/cost-control)) para não surpreender o cartão.

Não subas o Streamlit no mesmo projecto se a meta é minimizar custo. O bot Discord também não.

---

## Checklist

- [ ] Railway Trial/Free **não** aguentam 1,5 GB de modelos + ~2 GB RAM
- [ ] Hobby **não** é grátis ($5 + RAM a $10/GB/mês ≈ **$20** só de memória)
- [ ] GitHub Pages/Actions/Codespaces **não** substituem `POST /predict/game`
- [ ] $0 = Docker local + extensão em localhost
- [ ] Nuvem = **só a API**, always-on, 2 GB+ (Railway Hobby ou Render Standard)
