"""Criação de Embeds bonitos para o Discord."""

import discord
from datetime import datetime


def embed_previsao(arg_dictData: dict) -> discord.Embed:
    """
    Cria um Embed formatado com a previsão de um jogo.

    Parâmetros:
    - arg_dictData (dict): Resposta da API /predict/game.

    Retorna:
    - discord.Embed: Embed formatado.
    """
    var_dictGame = arg_dictData.get("game", {})
    var_dictClassificacao = arg_dictData.get("classificacao")
    var_dictRegressao = arg_dictData.get("regressao")

    # Cor baseada na classificação
    var_dictColorMap = {
        "cai": discord.Color.green(),      # Bom para o consumidor
        "mantem": discord.Color.gold(),
        "sobe": discord.Color.red(),        # Preço vai subir
    }
    var_objColor = var_dictColorMap.get(var_dictClassificacao["classe"], discord.Color.blurple()) if var_dictClassificacao else discord.Color.blurple()

    var_objEmbed = discord.Embed(
        title=f"🎮 {var_dictGame.get('name', 'Jogo')}",
        description=f"**AppID:** `{var_dictGame.get('appid', 'N/A')}`",
        color=var_objColor,
        timestamp=datetime.now(),
    )

    # Thumbnail (imagem do jogo)
    var_strHeader = var_dictGame.get("header_image")
    if var_strHeader:
        var_objEmbed.set_thumbnail(url=var_strHeader)

    # Info do jogo
    var_floatPrice = var_dictGame.get("price", 0)
    var_boolIsComingSoon = var_dictGame.get("is_coming_soon", False)
    var_strPrecoText = "Não Lançado" if var_boolIsComingSoon else (f"R$ {var_floatPrice:.2f}" if var_floatPrice > 0 else "Gratuito")
    var_intReview = var_dictGame.get("review_score", 0)
    var_objEmbed.add_field(
        name="💰 Preço Atual",
        value=var_strPrecoText,
        inline=True,
    )

    var_strReleaseDate = var_dictGame.get("release_date")
    if var_strReleaseDate:
        var_objEmbed.add_field(
            name="📅 Lançamento",
            value=var_strReleaseDate,
            inline=True,
        )
    var_objEmbed.add_field(
        name="⭐ Review Score",
        value=f"{var_intReview}%" if var_intReview else "N/A",
        inline=True,
    )

    # Classificação
    if var_dictClassificacao:
        # Barra de probabilidades
        var_strProbasText = ""
        for var_strLabel, var_floatProb in var_dictClassificacao["probabilidades"].items():
            var_intBarLen = int(var_floatProb * 10)
            var_strBar = "█" * var_intBarLen + "░" * (10 - var_intBarLen)
            var_strProbasText += f"`{var_strLabel:>6}: {var_strBar} {var_floatProb:.1%}`\n"

        var_objEmbed.add_field(
            name=f"📊 Direção do Preço: {var_dictClassificacao['classe_emoji']}",
            value=f"Confiança: **{var_dictClassificacao['confianca']:.1%}**\n{var_strProbasText}",
            inline=False,
        )

    # Regressão
    if var_dictRegressao:
        var_strValorRegressao = f"**{var_dictRegressao['dias_estimados']} dias**\n{var_dictRegressao['descricao']}"
        
        var_intDesconto = var_dictRegressao.get("desconto_previsto_pct", 0)
        if var_intDesconto > 0:
            var_floatPreco = var_dictRegressao.get("preco_estimado", 0.0)
            var_floatMargem = var_dictRegressao.get("desconto_margem_erro", 0.0)
            var_strPrecoFormatado = f"R$ {var_floatPreco:.2f}" if var_floatPreco > 0 else "Gratuito"
            var_strValorRegressao += f"\n\n🏷️ **Desconto Previsto:** {var_intDesconto}% (± {var_floatMargem}%)\n🎯 **Preço Estimado:** {var_strPrecoFormatado}"
            
        var_objEmbed.add_field(
            name="⏳ Próxima Promoção",
            value=var_strValorRegressao,
            inline=False,
        )

    var_listWarnings = arg_dictData.get("warnings", [])
    if var_listWarnings:
        var_strWarnings = "\n".join([f"⚠️ {w}" for w in var_listWarnings])
        var_objEmbed.add_field(
            name="Avisos",
            value=var_strWarnings,
            inline=False,
        )

    var_objEmbed.set_footer(text="Previsor Steam • Dados de ML")

    return var_objEmbed


def embed_status(arg_dictHealthData: dict) -> discord.Embed:
    """
    Cria Embed com o status da API.

    Parâmetros:
    - arg_dictHealthData (dict): Resposta do /health.

    Retorna:
    - discord.Embed: Embed formatado.
    """
    var_strStatus = arg_dictHealthData.get("status", "desconhecido")
    var_dictModels = arg_dictHealthData.get("models", {})

    var_objColor = discord.Color.green() if var_strStatus == "healthy" else discord.Color.red()

    var_objEmbed = discord.Embed(
        title="📡 Status da API — Previsor Steam",
        color=var_objColor,
        timestamp=datetime.now(),
    )

    var_objEmbed.add_field(
        name="Status",
        value=f"{'🟢' if var_strStatus == 'healthy' else '🔴'} {var_strStatus.upper()}",
        inline=True,
    )
    var_objEmbed.add_field(
        name="Versão",
        value=arg_dictHealthData.get("version", "N/A"),
        inline=True,
    )
    var_objEmbed.add_field(
        name="Modelos",
        value=(
            f"Classificação: {'✅' if var_dictModels.get('classificacao') else '❌'}\n"
            f"Regressão: {'✅' if var_dictModels.get('regressao_dias') else '❌'}\n"
            f"Pipeline: {'✅' if var_dictModels.get('pipeline_escalonamento') else '❌'}"
        ),
        inline=False,
    )

    return var_objEmbed


def embed_busca(arg_listResults: list[dict], arg_strQuery: str) -> discord.Embed:
    """
    Cria Embed com resultados de busca.

    Parâmetros:
    - arg_listResults (list): Lista de jogos encontrados.
    - arg_strQuery (str): Query original.

    Retorna:
    - discord.Embed: Embed formatado.
    """
    var_objEmbed = discord.Embed(
        title=f"🔍 Resultados para: \"{arg_strQuery}\"",
        color=discord.Color.blurple(),
        timestamp=datetime.now(),
    )

    if not arg_listResults:
        var_objEmbed.description = "Nenhum jogo encontrado."
        return var_objEmbed

    var_listLines = []
    for var_intIdx, var_dictGame in enumerate(arg_listResults[:10], 1):
        var_listLines.append(f"**{var_intIdx}.** {var_dictGame.get('name', '?')} (`{var_dictGame.get('appid', '?')}`)")

    var_objEmbed.description = "\n".join(var_listLines)
    var_objEmbed.set_footer(text=f"{len(arg_listResults)} resultado(s) • Use /prever <nome> para previsão")

    return var_objEmbed


def embed_erro(arg_strMessage: str) -> discord.Embed:
    """
    Cria Embed de erro.

    Parâmetros:
    - arg_strMessage (str): Mensagem de erro.

    Retorna:
    - discord.Embed: Embed de erro formatado.
    """
    return discord.Embed(
        title="❌ Erro",
        description=arg_strMessage,
        color=discord.Color.red(),
        timestamp=datetime.now(),
    )
