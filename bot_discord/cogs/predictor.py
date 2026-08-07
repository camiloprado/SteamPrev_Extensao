"""
Cog de previsão — Slash commands /prever, /buscar, /status.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

from bot_discord.api_client import APIClient
from bot_discord.embeds import embed_previsao, embed_status, embed_busca, embed_erro

logger = logging.getLogger("bot.predictor")


class PredictorCog(commands.Cog):
    """Cog com comandos de previsão de preços da Steam."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_client = APIClient()

    async def cog_unload(self):
        await self.api_client.close()

    @app_commands.command(name="prever", description="Prevê a direção do preço de um jogo da Steam")
    @app_commands.describe(jogo="Nome do jogo (ex: 'Elden Ring', 'Stardew Valley', 'Counter-Strike')")
    async def prever(self, interaction: discord.Interaction, jogo: str):
        """
        Faz a previsão completa de um jogo.
        Aceita nome do jogo (busca aproximada).
        """
        await interaction.response.defer(thinking=True)

        try:
            result = await self.api_client.predict_game(jogo)

            if result is None:
                await interaction.followup.send(
                    embed=embed_erro(f"Jogo não encontrado: **{jogo}**\n\nUse `/buscar` para procurar o nome correto."),
                    ephemeral=True,
                )
                return

            await interaction.followup.send(embed=embed_previsao(result))

        except Exception as e:
            logger.error(f"Erro no /prever: {e}")
            await interaction.followup.send(
                embed=embed_erro(f"Erro ao processar previsão: {str(e)}"),
                ephemeral=True,
            )

    @app_commands.command(name="buscar", description="Busca jogos na Steam pelo nome")
    @app_commands.describe(nome="Nome do jogo para buscar")
    async def buscar(self, interaction: discord.Interaction, nome: str):
        """Busca jogos pelo nome com resultado fuzzy."""
        await interaction.response.defer(thinking=True)

        try:
            results = await self.api_client.search_games(nome, limit=10)
            await interaction.followup.send(embed=embed_busca(results, nome))
        except Exception as e:
            logger.error(f"Erro no /buscar: {e}")
            await interaction.followup.send(
                embed=embed_erro(f"Erro na busca: {str(e)}"),
                ephemeral=True,
            )

    @app_commands.command(name="status", description="Verifica o status da API de previsão")
    async def status(self, interaction: discord.Interaction):
        """Verifica se a API está online e os modelos carregados."""
        await interaction.response.defer(thinking=True)

        try:
            health = await self.api_client.health()
            await interaction.followup.send(embed=embed_status(health))
        except Exception as e:
            logger.error(f"Erro no /status: {e}")
            await interaction.followup.send(
                embed=embed_erro(f"API indisponível: {str(e)}"),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Registra a cog no bot."""
    await bot.add_cog(PredictorCog(bot))
