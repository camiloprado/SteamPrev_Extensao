"""
Script de teste manual para as APIs (Steam e ITAD).
Permite ao desenvolvedor testar visualmente o retorno das classes recém-refatoradas.
"""

import asyncio
import os
import json
from rich.console import Console
from rich.panel import Panel
from core.steam_client import SteamClient
from core.itad_client import ITADClient

# Para testes isolados garantindo leitura do .env do Base (caso necessário pro ITAD)
from dotenv import load_dotenv
var_strBaseEnvPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Projeto_TCC_CC", ".env"))
if os.path.exists(var_strBaseEnvPath):
    load_dotenv(var_strBaseEnvPath, override=False)

console = Console()

async def teste_manual():
    # ID de teste: "Hollow Knight" (367520) ou Elden Ring (1245620)
    var_intAppID = 367520
    
    console.print(f"[bold cyan]Iniciando Teste Manual de APIs Reais para o AppID {var_intAppID}...[/bold cyan]")
    
    # 1. Teste da Steam API
    console.print("\n[bold yellow][1/2] Consultando Steam Store API (Detalhes e Preço)...[/bold yellow]")
    var_dictSteamData = await SteamClient.get_game_data(var_intAppID)
    
    if var_dictSteamData:
        console.print(Panel(json.dumps(var_dictSteamData, indent=2, ensure_ascii=False), title="Retorno Steam API"))
    else:
        console.print("[bold red]Falha ao obter dados da Steam.[/bold red]")
        return

    # 2. Teste da ITAD API V2
    console.print("\n[bold yellow][2/2] Consultando ITAD API V2 (Histórico de Preços)...[/bold yellow]")
    
    var_floatPrice = var_dictSteamData.get("price", 0.0)
    var_listHistory = await ITADClient.get_price_history(var_intAppID, arg_floatPrecoBase=var_floatPrice, arg_intAnos=1)
    
    if var_listHistory:
        console.print(f"[bold green]Historico obtido com sucesso! Total de registros (1 ano): {len(var_listHistory)}[/bold green]")
        # Mostrando apenas os primeiros 3 eventos
        var_listAmostra = var_listHistory[:3]
        console.print(Panel(json.dumps(var_listAmostra, indent=2, ensure_ascii=False), title="Amostra (3 primeiros registros ITAD)"))
    else:
        console.print("[bold yellow]Historico vazio ou API Key ITAD ausente/invalida.[/bold yellow]")

if __name__ == "__main__":
    asyncio.run(teste_manual())
