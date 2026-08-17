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
        self._var_dictClassificacaoModels = {}
        self._var_dictRegressaoModels = {}
        self._var_dictRegressaoDescontoModels = {}
        self._var_objPipelineEscalonamento = None
        
        self._var_dictClassificacaoMtime = {}
        self._var_dictRegressaoMtime = {}
        self._var_dictRegressaoDescontoMtime = {}
        
        self._var_boolLoaded = False
        self._var_strCurrentHorizon = "latest"

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
        # Pré-carrega todos os horizontes para evitar lentidão na troca
        for var_strHoriz in ["30d", "60d", "90d", "latest"]:
            self.ensure_models_for_horizon(var_strHoriz)

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
        self._var_strCurrentHorizon = var_strHorizonte

        # ── Resolve caminhos com fallback ──
        # Classificação: tenta nomenclatura padronizada primeiro
        if var_strHorizonte == "latest":
            var_pathClassificacao = self._var_pathModels / "modelo_latest.joblib"
        else:
            var_pathClassificacao = self._var_pathModels / f"modelo_classificacao_{var_strHorizonte}.joblib"

        # Fallback: nomenclatura antiga com algoritmo
        if not var_pathClassificacao.exists():
            var_pathClassificacao = self._var_pathModels / f"modelo_classificacao_XGBoost_{horizonte}.joblib"

        # Regressão Dias: tenta nomenclatura padronizada primeiro
        if var_strHorizonte == "latest":
            var_pathRegressao = self._var_pathModels / "modelo_regressao_dias_30d.joblib"
        else:
            var_pathRegressao = self._var_pathModels / f"modelo_regressao_dias_{var_strHorizonte}.joblib"

        # Fallback: nomenclatura antiga
        if not var_pathRegressao.exists():
            var_pathRegressao = self._var_pathModels / f"modelo_regressao_XGBoost_{horizonte}.joblib"
        if not var_pathRegressao.exists():
            var_pathRegressao = self._var_pathModels / f"modelo_regressao_{var_strHorizonte}.joblib"
            
        # Regressão Desconto:
        if var_strHorizonte == "latest":
            var_pathRegressaoDesconto = self._var_pathModels / "modelo_regressao_desconto_30d.joblib"
        else:
            var_pathRegressaoDesconto = self._var_pathModels / f"modelo_regressao_desconto_{var_strHorizonte}.joblib"

        # Checa atualização do arquivo de Classificação
        if var_pathClassificacao.exists():
            var_floatMtime = var_pathClassificacao.stat().st_mtime
            if var_strHorizonte not in self._var_dictClassificacaoModels or var_floatMtime > self._var_dictClassificacaoMtime.get(var_strHorizonte, 0):
                logger.info(f"🔄 Carregando modelo de classificação para horizonte: {var_strHorizonte}")
                self._var_dictClassificacaoModels[var_strHorizonte] = joblib.load(var_pathClassificacao)
                self._var_dictClassificacaoMtime[var_strHorizonte] = var_floatMtime
                var_boolReloaded = True

        # Checa atualização do arquivo de Regressão Dias
        if var_pathRegressao.exists():
            var_floatMtime = var_pathRegressao.stat().st_mtime
            if var_strHorizonte not in self._var_dictRegressaoModels or var_floatMtime > self._var_dictRegressaoMtime.get(var_strHorizonte, 0):
                logger.info(f"🔄 Carregando modelo de regressão (dias) para horizonte: {var_strHorizonte}")
                self._var_dictRegressaoModels[var_strHorizonte] = joblib.load(var_pathRegressao)
                self._var_dictRegressaoMtime[var_strHorizonte] = var_floatMtime
                var_boolReloaded = True

        # Checa atualização do arquivo de Regressão Desconto
        if var_pathRegressaoDesconto.exists():
            var_floatMtime = var_pathRegressaoDesconto.stat().st_mtime
            if var_strHorizonte not in self._var_dictRegressaoDescontoModels or var_floatMtime > self._var_dictRegressaoDescontoMtime.get(var_strHorizonte, 0):
                logger.info(f"🔄 Carregando modelo de regressão (desconto) para horizonte: {var_strHorizonte}")
                self._var_dictRegressaoDescontoModels[var_strHorizonte] = joblib.load(var_pathRegressaoDesconto)
                self._var_dictRegressaoDescontoMtime[var_strHorizonte] = var_floatMtime
                var_boolReloaded = True

        if var_boolReloaded:
            gc.collect()

        return var_boolReloaded

    @property
    def is_loaded(self) -> bool:
        """Verifica se os modelos foram carregados."""
        return self._var_boolLoaded

    @property
    def classificacao_available(self) -> bool:
        """Verifica se o modelo de classificação está disponível no horizonte atual."""
        return self._var_strCurrentHorizon in self._var_dictClassificacaoModels

    @property
    def regressao_available(self) -> bool:
        """Verifica se o modelo de regressão (dias) está disponível no horizonte atual."""
        return self._var_strCurrentHorizon in self._var_dictRegressaoModels

    @property
    def regressao_desconto_available(self) -> bool:
        """Verifica se o modelo de regressão (desconto) está disponível no horizonte atual."""
        return self._var_strCurrentHorizon in self._var_dictRegressaoDescontoModels

    @property
    def classificacao_model(self):
        """Retorna o modelo de classificação carregado para o horizonte atual."""
        return self._var_dictClassificacaoModels.get(self._var_strCurrentHorizon)

    @property
    def regressao_model(self):
        """Retorna o modelo de regressão (dias) carregado para o horizonte atual."""
        return self._var_dictRegressaoModels.get(self._var_strCurrentHorizon)

    @property
    def regressao_desconto_model(self):
        """Retorna o modelo de regressão (desconto) carregado para o horizonte atual."""
        return self._var_dictRegressaoDescontoModels.get(self._var_strCurrentHorizon)

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
            "regressao_dias": self.regressao_available,
            "regressao_desconto": self.regressao_desconto_available,
            "pipeline_escalonamento": self._var_objPipelineEscalonamento is not None,
            "models_path": str(self._var_pathModels),
        }
