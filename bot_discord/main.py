"""
Bot Discord — Previsor Steam
Entrypoint principal do bot com slash commands.
"""

import discord
from discord.ext import commands
import logging
import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bot.main")


class PrevisorBot(commands.Bot):
    """Bot do Previsor Steam com slash commands."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            description="🎮 Previsor Steam — Previsão de preços de jogos",
        )

    async def setup_hook(self):
        """Carrega cogs e sincroniza commands."""
        await self.load_extension("bot_discord.cogs.predictor")
        logger.info("✅ Cog predictor carregada")

        # Sincroniza slash commands
        synced = await self.tree.sync()
        logger.info(f"✅ {len(synced)} comando(s) sincronizado(s)")

    async def on_ready(self):
        logger.info("═" * 60)
        logger.info(f"🤖 Bot conectado como: {self.user}")
        logger.info(f"   ID: {self.user.id}")
        logger.info(f"   Guilds: {len(self.guilds)}")
        logger.info("═" * 60)

        # Status customizado
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="preços na Steam 📊",
            )
        )


def main():
    """Inicia o bot."""
    token = os.getenv("DISCORD_TOKEN")

    if not token or token == "seu_token_do_discord_aqui":
        logger.error("❌ DISCORD_TOKEN não configurado!")
        logger.error("   Configure o token no arquivo .env")
        logger.error("   Crie um bot em: https://discord.com/developers/applications")
        sys.exit(1)

    bot = PrevisorBot()
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
