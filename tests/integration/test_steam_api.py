"""Testes de integração reais para a Steam API."""

import pytest
from core.steam_client import SteamClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_steam_api_real_call():
    """Valida se a Steam API oficial retorna o formato esperado para um jogo conhecido (CS2)."""
    # 730 = Counter-Strike 2
    var_dictData = await SteamClient.get_game_data(730)
    
    assert var_dictData is not None
    assert var_dictData["appid"] == 730
    assert "Counter-Strike" in var_dictData["name"]
    assert "price" in var_dictData
    assert var_dictData["is_free"] is True
    assert var_dictData["price"] == 0.0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_steam_api_paid_game():
    """Valida se a Steam API retorna preço corretamente para um jogo pago (Elden Ring)."""
    # 1245620 = ELDEN RING
    var_dictData = await SteamClient.get_game_data(1245620)
    
    assert var_dictData is not None
    assert var_dictData["appid"] == 1245620
    assert "ELDEN RING" in var_dictData["name"].upper()
    assert var_dictData["is_free"] is False
    assert var_dictData["price"] > 0.0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_steam_api_invalid_game():
    """Valida o comportamento da Steam API para um AppID inexistente."""
    var_dictData = await SteamClient.get_game_data(999999999)
    assert var_dictData is None
