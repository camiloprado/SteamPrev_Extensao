# SteamPrev — Previsão Inteligente de Preços 🎮

O **SteamPrev** é um ecossistema completo de predição de preços de jogos da Steam, projetado para auxiliar consumidores na tomada de decisões através de Inteligência Artificial. Ele consome modelos de Machine Learning (Classificação de Tendência e Regressão de Dias) previamente treinados.

Esta aplicação funciona extraindo dados em tempo real da loja da Steam e dados históricos da ITAD (Is There Any Deal), combinando-os num *Pipeline de Feature Engineering* antes de submetê-los aos modelos preditivos Random Forest e XGBoost.

## 🏗️ Arquitetura e Componentes

A arquitetura do SteamPrev é descentralizada e multicanal:

- **`api/` (Backend Core)**: Construída em **FastAPI**, expõe endpoints assíncronos (`/predict/game`). Consome as APIs da Steam e ITAD, formata os dados e executa a inferência nos arquivos `.joblib`. Implementa roteamento dinâmico dos modelos baseado na janela temporal escolhida.
- **`extension/` (Interface Frontend)**: Extensão de navegador (Manifest V3 - Chrome, Edge, Brave, Opera) desenvolvida em Vanilla JS/HTML/CSS. Injeta um *popup* na loja da Steam capturando o ID do jogo da URL atual, se comunicando com o backend para exibir probabilidades preditivas.
- **`dashboard/` (Interface Dashlit)**: Aplicação **Streamlit** criada para uma consulta em tela cheia e análises mais detalhadas, agindo como um portal independente para consultar jogos pelo AppID.
- **`bot_discord/` (Discord Bot)**: Integração via comandos slash (`/prever`) para que usuários consultem as predições diretamente no Discord.
- **`core/` (Lógica de Negócios)**: Contém o cliente HTTP, o extrator de features complexas (conversões cambiais, janelas temporais de promoções) e os early returns.

## ⚙️ Instalação / Configuração

O projeto pode ser clonado e executado em qualquer máquina, porém requer duas dependências manuais críticas (Chaves de API e os Modelos de ML):

### 1. Variáveis de Ambiente (`.env`)
Você precisa criar um arquivo chamado `.env` na raiz do projeto contendo as seguintes chaves:
```ini
# Token do bot no Discord (Obrigatório para ligar o Bot)
DISCORD_TOKEN=seu_token_aqui

# ITAD API Key v2 (Opcional, porém o histórico requere acesso válido)
ITAD_API_KEY=sua_chave_itad_aqui
```

### 2. Importando os Modelos (`.joblib`)
O sistema **não** inclui os arquivos pesados de Machine Learning no controle de versão.
No entanto, **não é necessário baixá-los manualmente**. A API possui um script integrado (`scripts/download_models.py`) que faz o download e a atualização automática da última versão dos modelos `.joblib` diretamente das [Tags de Release do GitHub](https://github.com/camiloprado/SteamPrev_Machine_Learning/releases/latest).

Os modelos baixados serão armazenados automaticamente no diretório:
`resources/models/`

### 3. Rodando os Serviços
Iniciando a API Principal:
```bash
uvicorn api.main:app --reload --port 8000
```
Iniciando o Dashboard (Streamlit):
```bash
streamlit run dashboard/app.py
```
Iniciando o Bot Discord:
```bash
python -m bot_discord.main
```

Para a **Extensão de Navegador**, habilite o "Modo do Desenvolvedor" na sua página de extensões (`chrome://extensions`) e clique em "Carregar sem compactação", selecionando a pasta `extension/` deste projeto.

## ✨ Features de Negócio

### Previsões Temporais Dinâmicas
O sistema foi refatorado para permitir que o usuário projete o futuro com base no horizonte analítico de sua preferência. A extensão e o dashboard enviam o parâmetro `horizonte` (*30 dias, 60 dias, 90 dias ou padrão*). O backend responde cirurgicamente roteando e carregando apenas o modelo equivalente a essa janela de dias na memória do servidor.

### Bypass de Promoção Inteligente (Early Return)
Como medida arquitetural defensiva e econômica, a aplicação aplica um *Early Return* dinâmico se constatar que um jogo **já se encontra em promoção no exato momento da busca**.
Se o usuário tentar prever o preço de algo que já está descontado:
- A engine de predição (`.joblib`) é ignorada, economizando RAM/CPU.
- Um bloco visual (*Sale Banner*) intercepta a tela, parabenizando o usuário pelo desconto ativo, ocultando gráficos e dispensando cargas operacionais desnecessárias.

## 🧪 Testes Automatizados
O projeto conta com mais de 14 suítes passando cobertura sobre integrações e simulações.
```bash
pytest tests/unit/ -v
```
