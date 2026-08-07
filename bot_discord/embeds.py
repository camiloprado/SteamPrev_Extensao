"""Criação de Embeds bonitos para o Discord."""

import discord
from datetime import datetime


def embed_previsao(data: dict) -> discord.Embed:
    """
    Cria um Embed formatado com a previsão de um jogo.

    Parâmetros:
    - data (dict): Resposta da API /predict/game.

    Retorna:
    - discord.Embed: Embed formatado.
    """
    game = data.get("game", {})
    clf = data.get("classificacao")
    reg = data.get("regressao")

    # Cor baseada na classificação
    color_map = {
        "cai": discord.Color.green(),      # Bom para o consumidor
        "mantem": discord.Color.gold(),
        "sobe": discord.Color.red(),        # Preço vai subir
    }
    color = color_map.get(clf["classe"], discord.Color.blurple()) if clf else discord.Color.blurple()

    embed = discord.Embed(
        title=f"🎮 {game.get('name', 'Jogo')}",
        description=f"**AppID:** `{game.get('appid', 'N/A')}`",
        color=color,
        timestamp=datetime.now(),
    )

    # Thumbnail (imagem do jogo)
    header = game.get("header_image")
    if header:
        embed.set_thumbnail(url=header)

    # Info do jogo
    price = game.get("price", 0)
    review = game.get("review_score", 0)
    embed.add_field(
        name="💰 Preço Atual",
        value=f"R$ {price:.2f}" if price > 0 else "Gratuito",
        inline=True,
    )
    embed.add_field(
        name="⭐ Review Score",
        value=f"{review}%" if review else "N/A",
        inline=True,
    )

    # Classificação
    if clf:
        # Barra de probabilidades
        probas_text = ""
        for label, prob in clf["probabilidades"].items():
            bar_len = int(prob * 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            probas_text += f"`{label:>6}: {bar} {prob:.1%}`\n"

        embed.add_field(
            name=f"📊 Direção do Preço: {clf['classe_emoji']}",
            value=f"Confiança: **{clf['confianca']:.1%}**\n{probas_text}",
            inline=False,
        )

    # Regressão
    if reg:
        embed.add_field(
            name="⏳ Próxima Promoção",
            value=f"**{reg['dias_estimados']} dias**\n{reg['descricao']}",
            inline=False,
        )

    embed.set_footer(text="Previsor Steam • Dados de ML")

    return embed


def embed_status(health_data: dict) -> discord.Embed:
    """
    Cria Embed com o status da API.

    Parâmetros:
    - health_data (dict): Resposta do /health.

    Retorna:
    - discord.Embed: Embed formatado.
    """
    status = health_data.get("status", "desconhecido")
    models = health_data.get("models", {})

    color = discord.Color.green() if status == "healthy" else discord.Color.red()

    embed = discord.Embed(
        title="📡 Status da API — Previsor Steam",
        color=color,
        timestamp=datetime.now(),
    )

    embed.add_field(
        name="Status",
        value=f"{'🟢' if status == 'healthy' else '🔴'} {status.upper()}",
        inline=True,
    )
    embed.add_field(
        name="Versão",
        value=health_data.get("version", "N/A"),
        inline=True,
    )
    embed.add_field(
        name="Modelos",
        value=(
            f"Classificação: {'✅' if models.get('classificacao') else '❌'}\n"
            f"Regressão: {'✅' if models.get('regressao') else '❌'}\n"
            f"Pipeline: {'✅' if models.get('pipeline_escalonamento') else '❌'}"
        ),
        inline=False,
    )

    return embed


def embed_busca(results: list[dict], query: str) -> discord.Embed:
    """
    Cria Embed com resultados de busca.

    Parâmetros:
    - results (list): Lista de jogos encontrados.
    - query (str): Query original.

    Retorna:
    - discord.Embed: Embed formatado.
    """
    embed = discord.Embed(
        title=f"🔍 Resultados para: \"{query}\"",
        color=discord.Color.blurple(),
        timestamp=datetime.now(),
    )

    if not results:
        embed.description = "Nenhum jogo encontrado."
        return embed

    lines = []
    for i, game in enumerate(results[:10], 1):
        lines.append(f"**{i}.** {game.get('name', '?')} (`{game.get('appid', '?')}`)")

    embed.description = "\n".join(lines)
    embed.set_footer(text=f"{len(results)} resultado(s) • Use /prever <nome> para previsão")

    return embed


def embed_erro(message: str) -> discord.Embed:
    """Cria Embed de erro."""
    return discord.Embed(
        title="❌ Erro",
        description=message,
        color=discord.Color.red(),
        timestamp=datetime.now(),
    )
