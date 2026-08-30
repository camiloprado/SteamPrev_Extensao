"""
Download automático de modelos ML do GitHub Releases.

Verifica se os modelos .joblib estão presentes localmente e, se ausentes,
faz o download automático a partir do repositório de modelos no GitHub Releases.

Fluxo:
    1. Busca manifest.json remoto para obter lista de modelos e SHA-256
    2. Compara com os arquivos locais (existência + integridade)
    3. Baixa apenas os modelos ausentes ou desatualizados
    4. Verifica integridade pós-download via SHA-256

Uso:
    # Na inicialização da API (chamado pelo models_loader.py)
    from scripts.download_models import ensure_models
    ensure_models(arg_pathModelsDir=Path("resources/models"))

    # Standalone via linha de comando
    python -m scripts.download_models
    python -m scripts.download_models --force            # Re-download forçado
    python -m scripts.download_models --dry-run           # Apenas verifica
"""

import hashlib
import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("steamprev.download_models")

# ── Configurações Padrão ──────────────────────────────────────────────────────

# URL base do GitHub Releases (usa redirect /latest/download/ para pegar a release mais recente)
CON_STR_GITHUB_RELEASES_BASE = (
    "https://github.com/camiloprado/SteamPrev_Machine_Learning/releases/latest/download"
)

# Diretório de destino padrão (relativo ao projeto)
CON_PATH_DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[1] / "resources" / "models"
CON_PATH_DEFAULT_DADOS_DIR = Path(__file__).resolve().parents[1] / "resources" / "dados"

# Catálogo de nomes/appids (busca por nome) publicado pela Fábrica junto do manifest dos modelos.
CON_STR_APPLIST_FILENAME = "steam_applist.json"

# Lista de modelos esperados para download
CON_LIST_EXPECTED_MODELS = [
    "modelo_latest.joblib",
    "modelo_classificacao_30d.joblib",
    "modelo_classificacao_60d.joblib",
    "modelo_classificacao_90d.joblib",
    "modelo_regressao_dias_30d.joblib",
    "modelo_regressao_dias_60d.joblib",
    "modelo_regressao_dias_90d.joblib",
    "modelo_regressao_desconto_30d.joblib",
    "modelo_regressao_desconto_60d.joblib",
    "modelo_regressao_desconto_90d.joblib",
]


def _calcular_sha256(arg_pathArquivo: Path) -> str:
    """
    Calcula o hash SHA-256 de um arquivo local.

    Parâmetros:
    - arg_pathArquivo (Path): Caminho do arquivo.

    Retorna:
    - str: Hash SHA-256 hexadecimal.
    """
    var_objHash = hashlib.sha256()
    with open(arg_pathArquivo, "rb") as var_fileObj:
        for var_bytesChunk in iter(lambda: var_fileObj.read(8192), b""):
            var_objHash.update(var_bytesChunk)
    return var_objHash.hexdigest()


def _download_arquivo(arg_strUrl: str, arg_pathDestino: Path) -> bool:
    """
    Faz download de um arquivo com log de progresso.

    Parâmetros:
    - arg_strUrl (str): URL do arquivo.
    - arg_pathDestino (Path): Caminho local de destino.

    Retorna:
    - bool: True se o download foi bem-sucedido, False caso contrário.
    """
    try:
        import requests
    except ImportError:
        logger.error(
            "Módulo 'requests' não instalado. "
            "Execute: pip install requests"
        )
        return False

    try:
        var_objResponse = requests.get(arg_strUrl, stream=True, timeout=120)
        var_objResponse.raise_for_status()

        var_intTotal = int(var_objResponse.headers.get("content-length", 0))
        var_floatTamanhoMb = var_intTotal / (1024 * 1024) if var_intTotal else 0

        logger.info(
            f"📥 Downloading {arg_pathDestino.name} "
            f"({var_floatTamanhoMb:.1f} MB)..."
        )

        arg_pathDestino.parent.mkdir(parents=True, exist_ok=True)

        var_intDownloaded = 0
        with open(arg_pathDestino, "wb") as var_fileObj:
            for var_bytesChunk in var_objResponse.iter_content(chunk_size=8192):
                var_fileObj.write(var_bytesChunk)
                var_intDownloaded += len(var_bytesChunk)

        logger.info(f"✅ {arg_pathDestino.name} baixado com sucesso.")
        return True

    except Exception as e:
        logger.error(f"❌ Falha ao baixar {arg_pathDestino.name}: {e}")
        # Remove arquivo parcial/corrompido
        if arg_pathDestino.exists():
            arg_pathDestino.unlink()
        return False


def _obter_manifest_remoto(arg_strBaseUrl: str, arg_pathModelsDir: Path) -> dict | None:
    """
    Obtém o manifest.json remoto do GitHub Releases.
    Salva cópia local como fallback para uso offline.

    Parâmetros:
    - arg_strBaseUrl (str): URL base do GitHub Releases.
    - arg_pathModelsDir (Path): Diretório local de modelos.

    Retorna:
    - dict | None: Conteúdo do manifest ou None se indisponível.
    """
    try:
        import requests
    except ImportError:
        logger.warning("Módulo 'requests' não instalado. Usando manifest local se disponível.")
        return _obter_manifest_local(arg_pathModelsDir)

    var_strManifestUrl = f"{arg_strBaseUrl}/manifest.json"
    var_pathManifestLocal = arg_pathModelsDir / "manifest.json"

    try:
        var_objResponse = requests.get(var_strManifestUrl, timeout=30)
        var_objResponse.raise_for_status()
        var_dictManifest = var_objResponse.json()

        # Salva cópia local para uso futuro offline
        with open(var_pathManifestLocal, "w", encoding="utf-8") as var_fileObj:
            json.dump(var_dictManifest, var_fileObj, indent=2, ensure_ascii=False)

        logger.info(f"📋 Manifest remoto carregado (versão: {var_dictManifest.get('version', 'N/A')})")
        return var_dictManifest

    except Exception as e:
        logger.warning(f"⚠️  Não foi possível obter manifest remoto: {e}")
        return _obter_manifest_local(arg_pathModelsDir)


def _obter_manifest_local(arg_pathModelsDir: Path) -> dict | None:
    """
    Carrega manifest.json local como fallback.

    Parâmetros:
    - arg_pathModelsDir (Path): Diretório local de modelos.

    Retorna:
    - dict | None: Conteúdo do manifest ou None se inexistente.
    """
    var_pathManifest = arg_pathModelsDir / "manifest.json"
    if var_pathManifest.exists():
        try:
            with open(var_pathManifest, "r", encoding="utf-8") as var_fileObj:
                var_dictManifest = json.load(var_fileObj)
            logger.info("📋 Usando manifest local existente.")
            return var_dictManifest
        except Exception as e:
            logger.warning(f"Falha ao ler manifest local: {e}")
    return None


def ensure_models(
    arg_pathModelsDir: Path | str | None = None,
    arg_strBaseUrl: str | None = None,
    arg_boolForce: bool = False,
) -> bool:
    """
    Garante que todos os modelos necessários estão presentes localmente.

    Se um modelo estiver ausente ou com hash diferente do manifest,
    faz o download automático do GitHub Releases.

    Parâmetros:
    - arg_pathModelsDir (Path | str | None): Diretório local de modelos. Default: resources/models.
    - arg_strBaseUrl (str | None): URL base do GitHub Releases. Default: env MODELS_BASE_URL ou constante.
    - arg_boolForce (bool): Se True, força re-download mesmo que o arquivo exista.

    Retorna:
    - bool: True se todos os modelos estão disponíveis, False caso contrário.
    """
    var_pathModelsDir = Path(arg_pathModelsDir) if arg_pathModelsDir else CON_PATH_DEFAULT_MODELS_DIR
    var_strBaseUrl = arg_strBaseUrl or os.getenv("MODELS_BASE_URL", CON_STR_GITHUB_RELEASES_BASE)

    var_pathModelsDir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 50)
    logger.info("VERIFICAÇÃO DE MODELOS ML")
    logger.info(f"Diretório: {var_pathModelsDir}")
    logger.info(f"Origem: {var_strBaseUrl}")
    logger.info("=" * 50)

    # 1. Buscar manifest remoto
    var_dictManifest = _obter_manifest_remoto(var_strBaseUrl, var_pathModelsDir)

    # 2. Determinar quais modelos verificar/baixar (steam_applist.json tem destino
    # próprio via ensure_applist() e não pertence a resources/models/).
    var_dictModelsInfo = var_dictManifest.get("models", {}) if var_dictManifest else {}
    var_listModelsToCheck = (
        [var_strNome for var_strNome in var_dictModelsInfo.keys() if var_strNome != CON_STR_APPLIST_FILENAME]
        if var_dictModelsInfo
        else CON_LIST_EXPECTED_MODELS
    )

    # 3. Verificar cada modelo
    var_boolAllOk = True
    var_intDownloaded = 0
    var_intSkipped = 0

    for var_strFilename in var_listModelsToCheck:
        var_pathLocal = var_pathModelsDir / var_strFilename

        # Verifica se existe
        if var_pathLocal.exists() and not arg_boolForce:
            # Se temos manifest, verifica hash
            if var_strFilename in var_dictModelsInfo:
                var_strExpectedHash = var_dictModelsInfo[var_strFilename].get("sha256", "")
                if var_strExpectedHash:
                    var_strActualHash = _calcular_sha256(var_pathLocal)
                    if var_strActualHash == var_strExpectedHash:
                        logger.debug(f"✅ {var_strFilename} — hash confere.")
                        var_intSkipped += 1
                        continue
                    else:
                        logger.info(
                            f"🔄 {var_strFilename} — hash diferente, re-downloading..."
                        )
                else:
                    logger.debug(f"✅ {var_strFilename} — existe (sem hash no manifest).")
                    var_intSkipped += 1
                    continue
            else:
                logger.debug(f"✅ {var_strFilename} — já existe.")
                var_intSkipped += 1
                continue

        # Download necessário
        var_strUrl = f"{var_strBaseUrl}/{var_strFilename}"
        var_boolSuccess = _download_arquivo(var_strUrl, var_pathLocal)

        if var_boolSuccess:
            var_intDownloaded += 1

            # Verificação de integridade pós-download
            if var_strFilename in var_dictModelsInfo:
                var_strExpectedHash = var_dictModelsInfo[var_strFilename].get("sha256", "")
                if var_strExpectedHash:
                    var_strActualHash = _calcular_sha256(var_pathLocal)
                    if var_strActualHash != var_strExpectedHash:
                        logger.error(
                            f"❌ Hash mismatch para {var_strFilename}! "
                            f"Esperado: {var_strExpectedHash[:16]}... "
                            f"Obtido: {var_strActualHash[:16]}..."
                        )
                        var_boolAllOk = False
                    else:
                        logger.info(f"🔒 {var_strFilename} — integridade verificada (SHA-256).")
        else:
            var_boolAllOk = False

    # 4. Resumo
    logger.info("-" * 50)
    if var_boolAllOk:
        logger.info(
            f"✅ Modelos OK — {var_intDownloaded} baixados, {var_intSkipped} já existiam."
        )
    else:
        logger.warning(
            f"⚠️  Alguns modelos indisponíveis — {var_intDownloaded} baixados, "
            f"{var_intSkipped} já existiam. A API pode não funcionar corretamente."
        )

    return var_boolAllOk


def ensure_applist(
    arg_pathDadosDir: Path | str | None = None,
    arg_strBaseUrl: str | None = None,
    arg_boolForce: bool = False,
) -> bool:
    """
    Garante que o steam_applist.json (catálogo de busca por nome) está atualizado
    localmente. Mesma lógica de manifest/SHA-256 de ensure_models(), mas com
    destino em resources/dados/ em vez de resources/models/.

    Parâmetros:
    - arg_pathDadosDir (Path | str | None): Diretório local de dados. Default: resources/dados.
    - arg_strBaseUrl (str | None): URL base do GitHub Releases. Default: env MODELS_BASE_URL ou constante.
    - arg_boolForce (bool): Se True, força re-download mesmo que o arquivo exista.

    Retorna:
    - bool: True se o applist está disponível e íntegro, False caso contrário.
    """
    var_pathDadosDir = Path(arg_pathDadosDir) if arg_pathDadosDir else CON_PATH_DEFAULT_DADOS_DIR
    var_strBaseUrl = arg_strBaseUrl or os.getenv("MODELS_BASE_URL", CON_STR_GITHUB_RELEASES_BASE)

    var_pathDadosDir.mkdir(parents=True, exist_ok=True)
    var_pathLocal = var_pathDadosDir / CON_STR_APPLIST_FILENAME

    var_dictManifest = _obter_manifest_remoto(var_strBaseUrl, var_pathDadosDir)
    var_dictInfo = var_dictManifest.get("models", {}).get(CON_STR_APPLIST_FILENAME) if var_dictManifest else None

    if var_pathLocal.exists() and not arg_boolForce:
        if not var_dictInfo:
            logger.debug(f"✅ {CON_STR_APPLIST_FILENAME} — existe (sem entrada no manifest).")
            return True
        var_strExpectedHash = var_dictInfo.get("sha256", "")
        if var_strExpectedHash and _calcular_sha256(var_pathLocal) == var_strExpectedHash:
            logger.debug(f"✅ {CON_STR_APPLIST_FILENAME} — hash confere.")
            return True
        logger.info(f"🔄 {CON_STR_APPLIST_FILENAME} — hash diferente, re-downloading...")

    if not var_dictInfo:
        logger.warning(f"{CON_STR_APPLIST_FILENAME} não encontrado no manifest remoto.")
        return var_pathLocal.exists()

    var_strUrl = f"{var_strBaseUrl}/{CON_STR_APPLIST_FILENAME}"
    if not _download_arquivo(var_strUrl, var_pathLocal):
        return False

    var_strExpectedHash = var_dictInfo.get("sha256", "")
    if var_strExpectedHash and _calcular_sha256(var_pathLocal) != var_strExpectedHash:
        logger.error(f"❌ Hash mismatch para {CON_STR_APPLIST_FILENAME}!")
        return False

    logger.info(f"🔒 {CON_STR_APPLIST_FILENAME} — integridade verificada (SHA-256).")
    return True


def check_models(
    arg_pathModelsDir: Path | str | None = None,
) -> dict:
    """
    Verifica o status dos modelos locais sem fazer download.

    Parâmetros:
    - arg_pathModelsDir (Path | str | None): Diretório local de modelos.

    Retorna:
    - dict: Status de cada modelo esperado (presente, ausente, hash_ok).
    """
    var_pathModelsDir = Path(arg_pathModelsDir) if arg_pathModelsDir else CON_PATH_DEFAULT_MODELS_DIR
    var_dictStatus = {}

    for var_strFilename in CON_LIST_EXPECTED_MODELS:
        var_pathLocal = var_pathModelsDir / var_strFilename
        var_dictStatus[var_strFilename] = {
            "present": var_pathLocal.exists(),
            "size_bytes": var_pathLocal.stat().st_size if var_pathLocal.exists() else 0,
        }

    return var_dictStatus


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    var_objParser = argparse.ArgumentParser(
        description="Download automático de modelos ML do GitHub Releases"
    )
    var_objParser.add_argument(
        "--models-dir", type=str, default=None,
        help="Diretório de destino dos modelos"
    )
    var_objParser.add_argument(
        "--base-url", type=str, default=None,
        help="URL base do GitHub Releases"
    )
    var_objParser.add_argument(
        "--force", action="store_true",
        help="Força re-download mesmo que os modelos existam"
    )
    var_objParser.add_argument(
        "--dry-run", action="store_true",
        help="Apenas verifica quais modelos seriam baixados"
    )

    var_objArgs = var_objParser.parse_args()

    if var_objArgs.dry_run:
        logger.info("🔍 Modo dry-run: verificando status dos modelos locais...")
        var_dictStatus = check_models(arg_pathModelsDir=var_objArgs.models_dir)
        for var_strFilename, var_dictInfo in var_dictStatus.items():
            var_strIcon = "✅" if var_dictInfo["present"] else "❌"
            var_strSize = (
                f"({var_dictInfo['size_bytes'] / (1024*1024):.1f} MB)"
                if var_dictInfo["present"] else "(ausente)"
            )
            logger.info(f"  {var_strIcon} {var_strFilename} {var_strSize}")
    else:
        var_boolOk = ensure_models(
            arg_pathModelsDir=var_objArgs.models_dir,
            arg_strBaseUrl=var_objArgs.base_url,
            arg_boolForce=var_objArgs.force,
        )
        var_boolOk = ensure_applist(
            arg_strBaseUrl=var_objArgs.base_url,
            arg_boolForce=var_objArgs.force,
        ) and var_boolOk
        sys.exit(0 if var_boolOk else 1)
