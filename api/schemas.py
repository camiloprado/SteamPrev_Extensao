"""Pydantic schemas para request/response da API."""

from pydantic import BaseModel, Field
from typing import Optional


# ── Request Schemas ──────────────────────────────────────────────────────────

class GameQueryInput(BaseModel):
    """Input que aceita AppID ou nome do jogo."""
    query: str = Field(
        ...,
        description="AppID (número) ou nome do jogo. Aceita nomes aproximados.",
        examples=["730", "Counter-Strike", "Elden Ring", "stardew valley"],
    )


class GameFeaturesInput(BaseModel):
    """Input manual de features para predição direta (modo avançado)."""
    review_score: float = Field(default=0.0, ge=0, le=100, description="Score de reviews (0-100)")
    preco_catalogo: float = Field(default=0.0, ge=0, description="Preço atual no catálogo (BRL)")
    preco_atual_hist: float = Field(default=0.0, ge=0, description="Preço atual no histórico")
    preco_media_janela: float = Field(default=0.0, ge=0, description="Preço médio na janela")
    preco_std_janela: float = Field(default=0.0, ge=0, description="Desvio padrão na janela")
    preco_min_janela: float = Field(default=0.0, ge=0, description="Preço mínimo na janela")
    preco_max_janela: float = Field(default=0.0, ge=0, description="Preço máximo na janela")
    frequencia_descontos_por_ano: float = Field(default=0.0, ge=0, description="Freq. descontos/ano")
    dias_no_preco_atual: int = Field(default=0, ge=0, description="Dias no preço atual")
    ratio_preco_atual_vs_minimo: float = Field(default=1.0, ge=0, description="Ratio preço/mínimo")
    desconto_medio_janela: float = Field(default=0.0, ge=0, le=100, description="Desconto médio (%)")
    desconto_max_janela: float = Field(default=0.0, ge=0, le=100, description="Desconto máximo (%)")
    num_promocoes_janela: int = Field(default=0, ge=0, description="Nº de promoções")
    dias_janela: int = Field(default=0, ge=0, description="Dias na janela de análise")
    dias_desde_ultimo_desconto: int = Field(default=9999, ge=0, description="Dias desde último desconto")
    mes_atual: int = Field(default=1, ge=1, le=12, description="Mês atual (1-12)")
    dia_do_ano: int = Field(default=1, ge=1, le=366, description="Dia do ano (1-366)")
    dias_para_proxima_grande_promo: int = Field(default=0, ge=0, description="Dias até próxima grande sale")


# ── Response Schemas ─────────────────────────────────────────────────────────

class GameInfo(BaseModel):
    """Informações básicas do jogo encontrado."""
    appid: int
    name: str
    price: Optional[float] = None
    review_score: Optional[float] = None
    header_image: Optional[str] = None


class ClassificationResult(BaseModel):
    """Resultado da classificação (direção do preço)."""
    classe: str = Field(description="Classe predita: 'cai', 'mantem' ou 'sobe'")
    classe_emoji: str = Field(description="Classe com emoji para exibição")
    probabilidades: dict[str, float] = Field(description="Probabilidades para cada classe")
    confianca: float = Field(description="Confiança da predição (maior probabilidade)")


class RegressionResult(BaseModel):
    """Resultado da regressão (dias até promoção)."""
    dias_estimados: int = Field(description="Dias estimados até a próxima promoção")
    descricao: str = Field(description="Descrição legível do resultado")


class PredictionResponse(BaseModel):
    """Resposta completa de predição."""
    game: GameInfo
    classificacao: Optional[ClassificationResult] = None
    regressao: Optional[RegressionResult] = None
    features_utilizadas: Optional[dict] = None


class SearchResult(BaseModel):
    """Resultado de busca de jogos."""
    results: list[GameInfo]
    total: int
    query: str


class HealthResponse(BaseModel):
    """Resposta do endpoint de health check."""
    status: str
    models: dict
    version: str = "1.0.0"
    timestamp: str
