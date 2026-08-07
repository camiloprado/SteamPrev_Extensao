"""
Carregador e gerenciador de modelos .joblib.
Carrega na inicialização e suporta hot-reload via timestamp do arquivo.
"""

import joblib
import logging
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("api.models_loader")


class ModelManager:
    """Gerencia o carregamento e reload dos modelos de ML."""

    def __init__(self, models_path: str):
        self.models_path = Path(models_path)
        self.classificacao_model = None
        self.regressao_model = None
        self.pipeline_escalonamento = None
        self._classificacao_mtime: float = 0.0
        self._regressao_mtime: float = 0.0
        self._loaded = False

    def load_models(self) -> None:
        """Carrega todos os modelos .joblib do diretório configurado."""
        logger.info(f"Carregando modelos de: {self.models_path}")

        # Classificação XGBoost
        clf_path = self.models_path / "modelo_classificacao_XGBoost_latest.joblib"
        if clf_path.exists():
            self.classificacao_model = joblib.load(clf_path)
            self._classificacao_mtime = clf_path.stat().st_mtime
            logger.info(f"✅ Classificação carregado: {clf_path.name}")
        else:
            logger.warning(f"⚠️ Modelo de classificação não encontrado: {clf_path}")

        # Regressão XGBoost
        reg_path = self.models_path / "modelo_regressao_XGBoost_latest.joblib"
        if reg_path.exists():
            self.regressao_model = joblib.load(reg_path)
            self._regressao_mtime = reg_path.stat().st_mtime
            logger.info(f"✅ Regressão carregado: {reg_path.name}")
        else:
            logger.warning(f"⚠️ Modelo de regressão não encontrado: {reg_path}")

        # Pipeline de escalonamento (se existir)
        pipe_path = self.models_path / "pipeline_escalonamento.joblib"
        if pipe_path.exists():
            self.pipeline_escalonamento = joblib.load(pipe_path)
            logger.info(f"✅ Pipeline escalonamento carregado: {pipe_path.name}")

        self._loaded = True
        logger.info("Carregamento de modelos concluído.")

    def check_and_reload(self) -> bool:
        """
        Verifica se os modelos foram atualizados e recarrega se necessário.

        Retorna:
        - bool: True se houve reload, False caso contrário.
        """
        reloaded = False

        clf_path = self.models_path / "modelo_classificacao_XGBoost_latest.joblib"
        if clf_path.exists() and clf_path.stat().st_mtime > self._classificacao_mtime:
            logger.info("🔄 Detectada atualização no modelo de classificação. Recarregando...")
            self.classificacao_model = joblib.load(clf_path)
            self._classificacao_mtime = clf_path.stat().st_mtime
            reloaded = True

        reg_path = self.models_path / "modelo_regressao_XGBoost_latest.joblib"
        if reg_path.exists() and reg_path.stat().st_mtime > self._regressao_mtime:
            logger.info("🔄 Detectada atualização no modelo de regressão. Recarregando...")
            self.regressao_model = joblib.load(reg_path)
            self._regressao_mtime = reg_path.stat().st_mtime
            reloaded = True

        return reloaded

    @property
    def is_loaded(self) -> bool:
        """Verifica se os modelos foram carregados."""
        return self._loaded

    @property
    def classificacao_available(self) -> bool:
        return self.classificacao_model is not None

    @property
    def regressao_available(self) -> bool:
        return self.regressao_model is not None

    def get_status(self) -> dict:
        """Retorna status dos modelos carregados."""
        return {
            "loaded": self._loaded,
            "classificacao": self.classificacao_available,
            "regressao": self.regressao_available,
            "pipeline_escalonamento": self.pipeline_escalonamento is not None,
            "models_path": str(self.models_path),
        }
