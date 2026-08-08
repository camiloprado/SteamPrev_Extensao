"""
Configuração do pytest e proteção do ambiente (Sandbox) para a extensão.
"""

import os
import pytest
from dotenv import load_dotenv

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(request):
    """
    Controla o ambiente baseado no marker do teste.
    Se for integration, carrega o .env real (buscando também no projeto base se necessário).
    Se for unit, garante que não teremos chaves de produção vazando.
    """
    var_listMarkers = [mark.name for item in request.session.items for mark in item.iter_markers()]
    
    if "integration" in var_listMarkers:
        # Carrega dotenv padrão da extensão
        load_dotenv()
        
        # Tenta carregar as chaves do projeto base como fallback,
        # caso não estejam no .env da extensão (homologação/integração)
        var_strBaseEnvPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Projeto_TCC_CC", ".env"))
        if os.path.exists(var_strBaseEnvPath):
            load_dotenv(var_strBaseEnvPath, override=False)
            
    else:
        # Modo Unit (proteção sandbox)
        # Seta chaves dummy caso algum código tente validar a presença delas.
        os.environ["ITAD_API_KEY"] = "MOCKED_UNIT_KEY_123"
        os.environ["STEAM_API_KEY"] = "MOCKED_STEAM_KEY"
