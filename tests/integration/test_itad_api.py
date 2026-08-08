"""Testes de integração reais para a ITAD API."""

import pytest
import os
from core.itad_client import ITADClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_itad_api_real_call():
    """Valida se a ITAD API retorna o histórico real (V2)."""
    # Só testamos se tivermos a API KEY, caso contrário o teste seria flacky no CI/CD
    if not os.getenv("ITAD_API_KEY") or os.getenv("ITAD_API_KEY") == "MOCKED_UNIT_KEY_123":
        pytest.skip("ITAD_API_KEY não configurada no ambiente real. Pulando teste de integração ITAD.")

    # 1245620 = ELDEN RING
    var_listHistory = await ITADClient.get_price_history(1245620, arg_floatPrecoBase=249.90, arg_intAnos=1)
    
    # É perfeitamente normal vir histórico vazio se o jogo não teve promoções nesse período,
    # ou se a API retornar, mas pelo menos validamos que é uma lista e não quebra com exceção.
    assert isinstance(var_listHistory, list)
    if len(var_listHistory) > 0:
        assert "timestamp" in var_listHistory[0]
        assert "preco" in var_listHistory[0]
        assert "desconto" in var_listHistory[0]
