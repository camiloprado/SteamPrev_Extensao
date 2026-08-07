# Previsor Steam Extensão — Walkthrough de Conclusão

Todo o projeto foi implementado com sucesso! A arquitetura agora abriga todo o ecossistema do **Previsor Steam** em um único repositório orquestrado com Docker.

## 🚀 Arquitetura e Implementação

Criamos uma infraestrutura de microserviços onde a API atua como o *cérebro* do sistema e os outros serviços (Bot, Dashboard e Extensão) consomem as predições.

1. **Core e Inteligência:**
   - Implementamos a mesma lógica de **Feature Engineering** (18 features e regra da janela de 5 anos) encontrada em `normalizar_modelos.py`.
   - Construímos Mocks para as APIs da Steam e do *IsThereAnyDeal* (ITAD) no diretório `core/`, de forma que o sistema responda instantaneamente sem requerer chaves de API nesta fase inicial.
   - Migramos o catálogo de jogos (`steam_applist.json`) e adicionamos uma busca inteligente (*fuzzy search*), permitindo que você digite "Elden Ring" ou "Counter-Strike" sem saber o AppID exato.
   - Adicionamos a lógica de hot-reload na classe `ModelManager`: ela recarrega modelos `.joblib` em cache automaticamente se notar alguma modificação no sistema de arquivos.

2. **API (FastAPI):**
   - Construída sobre o `uvicorn` e preparada para inferência rápida.
   - Expõe endpoints consolidados como `/predict/game` que realiza toda a ingestão, limpeza de features e gera a **classificação** (Probabilidade de queda/manutenção/subida) e **regressão** (Dias até o desconto).
   - Suíte completa de testes (`pytest`) cobrindo as rotas principais. Todos os 16 testes criados **passaram com sucesso** (Verificação aprovada ✅).

3. **Bot no Discord:**
   - Construído com `discord.py` através do padrão de Cogs.
   - Comandos slash integrados: `/prever <nome_do_jogo>`, `/buscar` e `/status`.
   - Gera Embeds super trabalhados visualmente com formatação condicional baseada na resposta da IA e inclui **barras de probabilidade textuais**.

4. **Dashboard (Streamlit):**
   - Possui design premium que foge do clássico Streamlit "padrão", com tema escuro imersivo, cards "glassmorphism" e componentes em HTML/CSS customizado.
   - Página **1_previsao**: Inclui gráficos iterativos interativos com *Plotly* (ex: gráfico Gauge para os dias previstos de promoção).
   - Página **2_historico**: Simula análises temporais e evoluções de mercado.

5. **Extensão para Chrome:**
   - Manifest V3 limpo focado exclusivamente no layout.
   - O Popup é responsivo, carrega os dados e possui animações via CSS vanilla que simulam efeitos de loading.
   - Não requer inicialização complexa (HTML, JS, CSS puros comunicando-se com a API localmente na porta `8000`).

## 🛠️ Como Iniciar e Testar o Projeto

Você tem duas opções para iniciar: com Docker (recomendado) ou executando os processos localmente.

### Opção 1: Via Docker Compose (Tudo de uma vez)
Se você tiver o Docker instalado, essa é a forma mais fácil:
```bash
cd /home/camilo/Desktop/CC/TCC/PROJETO_TCC_CC_EXTENSAO
docker-compose up --build
```
Isso iniciará:
- **API** em `http://localhost:8000`
- **Dashboard** em `http://localhost:8501`
- **Bot Discord** (Desde que a key em `.env` esteja configurada corretamente)

> [!WARNING]
> Para o bot do Discord inicializar corretamente, não esqueça de abrir o arquivo `.env` gerado e colocar sua chave real no campo `DISCORD_TOKEN=`.

### Opção 2: Via Ambiente Virtual (Apenas API)
Caso queira subir apenas a API durante seu desenvolvimento:
```bash
cd /home/camilo/Desktop/CC/TCC/PROJETO_TCC_CC_EXTENSAO
source .venv/bin/activate
uvicorn api.main:app --reload
```
Acesse `http://127.0.0.1:8000/docs` no navegador para testar o **Swagger UI**.

## 🔌 Instalando a Extensão no Chrome
Para carregar a extensão desenvolvida:
1. Abra o navegador base Chromium (Chrome/Brave/Edge) e acesse `chrome://extensions/`
2. Ative o "Modo do Desenvolvedor" (Developer mode) no canto superior direito.
3. Clique em "Carregar sem compactação" (Load unpacked).
4. Selecione a pasta `/home/camilo/Desktop/CC/TCC/PROJETO_TCC_CC_EXTENSAO/extension`.
5. Clique no ícone da extensão no navegador para testar (Requer que a API esteja online na porta 8000).

> [!TIP]
> **Scripts Auxiliares**
> Caso precise re-gerar os modelos dummy no futuro (se estiver alterando features de teste, por exemplo), basta rodar `python scripts/generate_dummy_models.py`. Atualmente, nós já inserimos os modelos **reais** (copiados da sua pasta do previsor_steam) na pasta `resources/models`, então o sistema já operará de forma fidedigna.
