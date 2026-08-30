"""
Sincroniza modelos .joblib da Fábrica para a Extensão.

Copia o conteúdo de resources/models/export/ (Fábrica) para
resources/models/ (Extensão) após validar o manifest.json e, quando
presente, o SHA-256 de cada arquivo. O steam_applist.json do mesmo
manifest vai para resources/dados/ em vez de resources/models/.

Uso:
    python scripts/sync_models.py
    python scripts/sync_models.py --source "D:\\Projeto_TCC_CC\\prj_TCC_PREVISOR_STEAM\\resources\\models\\export" --dest "D:\\SteamPrev_Extensao\\resources\\models"
    python scripts/sync_models.py --dry-run
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger("steamprev.sync_models")

# Sobrescrever via env var FACTORY_MODELS_EXPORT_PATH em máquinas onde o
# repositório da Fábrica não está no caminho padrão de desenvolvimento.
CON_PATH_DEFAULT_SOURCE = Path(
    os.getenv(
        "FACTORY_MODELS_EXPORT_PATH",
        r"D:\Projeto_TCC_CC\prj_TCC_PREVISOR_STEAM\resources\models\export",
    )
)
CON_PATH_DEFAULT_DEST = Path(__file__).resolve().parents[1] / "resources" / "models"

# Catálogo de busca por nome: vem no mesmo manifest, mas o destino é resources/dados/, não resources/models/.
CON_STR_APPLIST_FILENAME = "steam_applist.json"


def _calcular_sha256(arg_pathArquivo: Path) -> str:
    """Calcula o hash SHA-256 de um arquivo local."""
    var_objHash = hashlib.sha256()
    with open(arg_pathArquivo, "rb") as var_fileObj:
        for var_bytesChunk in iter(lambda: var_fileObj.read(8192), b""):
            var_objHash.update(var_bytesChunk)
    return var_objHash.hexdigest()


def _carregar_manifest(arg_pathSource: Path) -> dict | None:
    """Carrega e valida a estrutura mínima do manifest.json de origem."""
    var_pathManifest = arg_pathSource / "manifest.json"
    if not var_pathManifest.exists():
        logger.error(f"manifest.json ausente em {arg_pathSource}")
        return None
    try:
        with open(var_pathManifest, "r", encoding="utf-8") as var_fileObj:
            var_dictManifest = json.load(var_fileObj)
    except Exception as e:
        logger.error(f"Falha ao ler manifest.json: {e}")
        return None
    if not isinstance(var_dictManifest, dict) or "models" not in var_dictManifest:
        logger.error("manifest.json inválido: campo 'models' ausente.")
        return None
    if not isinstance(var_dictManifest["models"], dict) or not var_dictManifest["models"]:
        logger.error("manifest.json inválido: lista de modelos vazia.")
        return None
    return var_dictManifest


def sync_models(
    arg_pathSource: Path | str | None = None,
    arg_pathDest: Path | str | None = None,
    arg_boolDryRun: bool = False,
) -> bool:
    """
    Copia modelos da Fábrica para a Extensão após validar o manifest.

    Parâmetros:
    - arg_pathSource: diretório de exportação da Fábrica.
    - arg_pathDest: diretório de modelos da Extensão.
    - arg_boolDryRun: se True, apenas reporta o que seria copiado.

    Retorna:
    - bool: True se todos os arquivos listados no manifest foram sincronizados.
    """
    var_pathSource = Path(arg_pathSource) if arg_pathSource else CON_PATH_DEFAULT_SOURCE
    var_pathDest = Path(arg_pathDest) if arg_pathDest else CON_PATH_DEFAULT_DEST

    logger.info("=" * 50)
    logger.info("SINCRONIZAÇÃO DE MODELOS")
    logger.info(f"Origem: {var_pathSource}")
    logger.info(f"Destino: {var_pathDest}")
    logger.info("=" * 50)

    if not var_pathSource.exists():
        logger.error(f"Diretório de origem não encontrado: {var_pathSource}")
        return False

    var_dictManifest = _carregar_manifest(var_pathSource)
    if var_dictManifest is None:
        return False

    logger.info(
        f"Manifest versão {var_dictManifest.get('version', 'N/A')} "
        f"({len(var_dictManifest['models'])} modelos)."
    )

    if not arg_boolDryRun:
        var_pathDest.mkdir(parents=True, exist_ok=True)

    var_boolAllOk = True
    var_intCopied = 0
    var_intSkipped = 0

    var_listArquivos = [
        var_strNome for var_strNome in var_dictManifest["models"].keys()
        if var_strNome != CON_STR_APPLIST_FILENAME
    ]
    if "manifest.json" not in var_listArquivos:
        var_listArquivos.append("manifest.json")

    for var_strFilename in var_listArquivos:
        var_pathOrigem = var_pathSource / var_strFilename
        var_pathDestino = var_pathDest / var_strFilename

        if not var_pathOrigem.exists():
            logger.error(f"Ausente na origem: {var_strFilename}")
            var_boolAllOk = False
            continue

        if var_strFilename != "manifest.json":
            var_strExpectedHash = var_dictManifest["models"].get(var_strFilename, {}).get("sha256", "")
            if var_strExpectedHash:
                var_strActualHash = _calcular_sha256(var_pathOrigem)
                if var_strActualHash != var_strExpectedHash:
                    logger.error(
                        f"SHA-256 inválido para {var_strFilename}: "
                        f"esperado {var_strExpectedHash[:16]}..., "
                        f"obtido {var_strActualHash[:16]}..."
                    )
                    var_boolAllOk = False
                    continue

        if arg_boolDryRun:
            logger.info(f"[dry-run] Copiaria {var_strFilename}")
            var_intSkipped += 1
            continue

        shutil.copy2(var_pathOrigem, var_pathDestino)
        logger.info(f"Copiado: {var_strFilename}")
        var_intCopied += 1

    # steam_applist.json vai para resources/dados/, irmã de resources/models/ (var_pathDest).
    if CON_STR_APPLIST_FILENAME in var_dictManifest["models"]:
        var_pathOrigemApplist = var_pathSource / CON_STR_APPLIST_FILENAME
        var_pathDestApplist = var_pathDest.parent / "dados" / CON_STR_APPLIST_FILENAME

        if not var_pathOrigemApplist.exists():
            logger.error(f"Ausente na origem: {CON_STR_APPLIST_FILENAME}")
            var_boolAllOk = False
        else:
            var_strExpectedHash = var_dictManifest["models"][CON_STR_APPLIST_FILENAME].get("sha256", "")
            if var_strExpectedHash and _calcular_sha256(var_pathOrigemApplist) != var_strExpectedHash:
                logger.error(f"SHA-256 inválido para {CON_STR_APPLIST_FILENAME}")
                var_boolAllOk = False
            elif arg_boolDryRun:
                logger.info(f"[dry-run] Copiaria {CON_STR_APPLIST_FILENAME} para {var_pathDestApplist}")
                var_intSkipped += 1
            else:
                var_pathDestApplist.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(var_pathOrigemApplist, var_pathDestApplist)
                logger.info(f"Copiado: {CON_STR_APPLIST_FILENAME} -> {var_pathDestApplist}")
                var_intCopied += 1

    logger.info("-" * 50)
    if arg_boolDryRun:
        logger.info(f"Dry-run: {var_intSkipped} arquivos seriam copiados.")
    else:
        logger.info(f"Sincronização: {var_intCopied} copiados.")
    return var_boolAllOk


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    var_objParser = argparse.ArgumentParser(
        description="Copia modelos da Fábrica para a Extensão validando o manifest.json"
    )
    var_objParser.add_argument(
        "--source", type=str, default=None,
        help="Diretório de exportação da Fábrica (resources/models/export)",
    )
    var_objParser.add_argument(
        "--dest", type=str, default=None,
        help="Diretório de modelos da Extensão (resources/models)",
    )
    var_objParser.add_argument(
        "--dry-run", action="store_true",
        help="Apenas verifica manifest e hashes, sem copiar",
    )
    var_objArgs = var_objParser.parse_args()

    var_boolOk = sync_models(
        arg_pathSource=var_objArgs.source,
        arg_pathDest=var_objArgs.dest,
        arg_boolDryRun=var_objArgs.dry_run,
    )
    sys.exit(0 if var_boolOk else 1)
