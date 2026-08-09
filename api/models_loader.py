"""
Carregador e gerenciador de modelos .joblib.
Carrega na inicialização e suporta hot-reload via timestamp do arquivo.
"""

import joblib
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("api.models_loader")


class ModelManager:
    """Gerencia o carregamento e reload dos modelos de ML."""

    def __init__(self, arg_strModelsPath: str):
        self._var_pathModels = Path(arg_strModelsPath)
        self._var_objClassificacaoModel = None
        self._var_objRegressaoModel = None
        self._var_objPipelineEscalonamento = None
        self._var_floatClassificacaoMtime: float = 0.0
        self._var_floatRegressaoMtime: float = 0.0
        self._var_boolLoaded = False
        self._var_strCurrentHorizon = None

    def load_models(self) -> None:
        """
        Carrega inicialmente os modelos base.
        Faz download automático de modelos ausentes via GitHub Releases.
        """
        import gc
        logger.info(f"Carregando pipeline de: {self._var_pathModels}")

        # Download automático de modelos ausentes
        try:
            from scripts.download_models import ensure_models
            ensure_models(models_dir=self._var_pathModels)
        except ImportError:
            logger.debug("Módulo download_models não disponível. Usando modelos locais.")
        except Exception as e:
            logger.warning(f"Download automático de modelos falhou: {e}")

        # Pipeline de escalonamento (único para todos os modelos)
        var_pathPipeline = self._var_pathModels / "pipeline_escalonamento.joblib"
        if var_pathPipeline.exists():
            self._var_objPipelineEscalonamento = joblib.load(var_pathPipeline)
            logger.info(f"✅ Pipeline escalonamento carregado: {var_pathPipeline.name}")

        self._var_boolLoaded = True
        # Defer model loading to endpoint execution
        self.ensure_models_for_horizon("latest")

    def ensure_models_for_horizon(self, horizonte: str) -> bool:
        """
        Garante que o modelo correspondente ao horizonte está na memória.
        Libera o antigo usando gc.collect() para evitar sobrecarga.
        Suporta hot-reload se o timestamp do arquivo mudar.

        Suporta nomenclatura padronizada (pós-exportação) e fallback
        para nomenclatura antiga com nome do algoritmo.
        """
        var_boolReloaded = False
        import gc

        # Normaliza: remove sufixo _latest se presente (ex: "30d_latest" → "30d")
        var_strHorizonte = horizonte.replace("_latest", "") if horizonte != "latest" else horizonte

        # ── Resolve caminhos com fallback ──
        # Classificação: tenta nomenclatura padronizada primeiro
        if var_strHorizonte == "latest":
            var_pathClassificacao = self._var_pathModels / "modelo_latest.joblib"
        else:
            var_pathClassificacao = self._var_pathModels / f"modelo_classificacao_{var_strHorizonte}.joblib"

        # Fallback: nomenclatura antiga com algoritmo
        if not var_pathClassificacao.exists():
            var_pathClassificacao = self._var_pathModels / f"modelo_classificacao_XGBoost_{horizonte}.joblib"

        # Regressão: tenta nomenclatura padronizada primeiro
        if var_strHorizonte == "latest":
            var_pathRegressao = self._var_pathModels / "modelo_regressao_30d.joblib"
        else:
            var_pathRegressao = self._var_pathModels / f"modelo_regressao_{var_strHorizonte}.joblib"

        # Fallback: nomenclatura antiga com algoritmo
        if not var_pathRegressao.exists():
            var_pathRegressao = self._var_pathModels / f"modelo_regressao_XGBoost_{horizonte}.joblib"
        
        # Fallback para regressão latest se não houver um específico pro horizonte
        if not var_pathRegressao.exists():
            var_pathRegressao = self._var_pathModels / "modelo_regressao_XGBoost_latest.joblib"

        var_boolHorizonChanged = self._var_strCurrentHorizon != var_strHorizonte

        # Checa atualização do arquivo de Classificação ou mudança de horizonte
        if var_pathClassificacao.exists():
            if var_boolHorizonChanged or var_pathClassificacao.stat().st_mtime > self._var_floatClassificacaoMtime:
                logger.info(f"🔄 Trocando/Recarregando modelo de classificação para horizonte: {var_strHorizonte}")
                self._var_objClassificacaoModel = None
                gc.collect() # Libera RAM do modelo antigo
                self._var_objClassificacaoModel = joblib.load(var_pathClassificacao)
                self._var_floatClassificacaoMtime = var_pathClassificacao.stat().st_mtime
                var_boolReloaded = True

        # Checa atualização do arquivo de Regressão
        if var_pathRegressao.exists():
            if var_boolHorizonChanged or var_pathRegressao.stat().st_mtime > self._var_floatRegressaoMtime:
                logger.info(f"🔄 Trocando/Recarregando modelo de regressão para horizonte: {var_strHorizonte}")
                self._var_objRegressaoModel = None
                gc.collect()
                self._var_objRegressaoModel = joblib.load(var_pathRegressao)
                self._var_floatRegressaoMtime = var_pathRegressao.stat().st_mtime
                var_boolReloaded = True

        self._var_strCurrentHorizon = var_strHorizonte
        return var_boolReloaded

    @property
    def is_loaded(self) -> bool:
        """Verifica se os modelos foram carregados."""
        return self._var_boolLoaded

    @property
    def classificacao_available(self) -> bool:
        """Verifica se o modelo de classificação está disponível."""
        return self._var_objClassificacaoModel is not None

    @property
    def regressao_available(self) -> bool:
        """Verifica se o modelo de regressão está disponível."""
        return self._var_objRegressaoModel is not None

    @property
    def classificacao_model(self):
        """Retorna o modelo de classificação carregado."""
        return self._var_objClassificacaoModel

    @property
    def regressao_model(self):
        """Retorna o modelo de regressão carregado."""
        return self._var_objRegressaoModel

    @property
    def pipeline_escalonamento(self):
        """Retorna o pipeline de escalonamento carregado."""
        return self._var_objPipelineEscalonamento

    def get_status(self) -> dict:
        """
        Retorna status dos modelos carregados.

        Retorna:
        - dict: Dicionário com status de cada modelo.
        """
        return {
            "loaded": self._var_boolLoaded,
            "classificacao": self.classificacao_available,
            "regressao": self.regressao_available,
            "pipeline_escalonamento": self._var_objPipelineEscalonamento is not None,
            "models_path": str(self._var_pathModels),
        }
