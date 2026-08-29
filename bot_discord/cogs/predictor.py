"""
Cog de previsão — Slash commands /prever, /buscar, /status.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

from bot_discord.api_client import APIClient
from bot_discord.embeds import embed_previsao, embed_status, embed_erro

logger = logging.getLogger("bot.predictor")


class PredictorCog(commands.Cog):
    """Cog com comandos de previsão de preços da Steam."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._var_objApiClient = APIClient()

    async def cog_unload(self):
        """Libera recursos ao descarregar a cog."""
        await self._var_objApiClient.close()

    @app_commands.command(name="prever", description="Prevê a direção do preço de um jogo da Steam")
    @app_commands.describe(
        appid="AppID numérico do jogo (ex: 1245620)",
        horizonte="Horizonte de tempo para previsão"
    )
    @app_commands.choices(horizonte=[
        app_commands.Choice(name="Padrão (Latest)", value="latest"),
        app_commands.Choice(name="30 Dias", value="30d_latest"),
        app_commands.Choice(name="60 Dias", value="60d_latest"),
        app_commands.Choice(name="90 Dias", value="90d_latest"),
    ])
    async def prever(
        self, 
        interaction: discord.Interaction, 
        appid: str, 
        horizonte: app_commands.Choice[str] = None
    ):
        """
        Faz a previsão completa de um jogo usando estritamente o AppID.
        """
        await interaction.response.defer(thinking=True)

        if not appid.isdigit():
            await interaction.followup.send(
                embed=embed_erro("Por favor, forneça apenas o **AppID numérico** do jogo. Buscas por nome não são mais suportadas."),
                ephemeral=True,
            )
            return

        var_strHorizonteValue = horizonte.value if horizonte else "latest"

        try:
            var_dictResult = await self._var_objApiClient.predict_game(appid, var_strHorizonteValue)

            if var_dictResult is None:
                await interaction.followup.send(
                    embed=embed_erro(f"Jogo não encontrado ou erro na API para o AppID: **{appid}**"),
                    ephemeral=True,
                )
                return

            await interaction.followup.send(embed=embed_previsao(var_dictResult))

        except Exception as e:
            logger.error(f"Erro no /prever: {e}")
            await interaction.followup.send(
                embed=embed_erro(f"Erro ao processar previsão: {str(e)}"),
                ephemeral=True,
            )



    @app_commands.command(name="status", description="Verifica o status da API de previsão")
    async def status(self, interaction: discord.Interaction):
        """Verifica se a API está online e os modelos carregados."""
        await interaction.response.defer(thinking=True)

        try:
            var_dictHealth = await self._var_objApiClient.health()
            await interaction.followup.send(embed=embed_status(var_dictHealth))
        except Exception as e:
            logger.error(f"Erro no /status: {e}")
            await interaction.followup.send(
                embed=embed_erro(f"API indisponível: {str(e)}"),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Registra a cog no bot."""
    await bot.add_cog(PredictorCog(bot))
