"""
Gera os ícones da extensão (16x16, 48x48, 128x128) a partir da imagem-fonte
da logo, sem distorcer a proporção do desenho.

Contexto/bug corrigido:
- A imagem-fonte é retangular (1376x768) com a logo pequena e centralizada.
  O script antigo fazia um resize direto da imagem inteira para cada tamanho
  quadrado (ex.: 128x128), o que ESMAGAVA/distorcia a logo.
- A imagem está em modo RGBA, mas o canal alpha é 100% opaco (255 em todos os
  pixels) — ou seja, apesar da aparência de "fundo transparente", o gerador de
  imagem (Gemini) "flatten"-ou o indicador visual de transparência (um padrão
  de xadrez cinza/branco) diretamente nos pixels RGB, sem gravar transparência
  real. Por isso, usar getbbox() direto no canal alpha original não funciona
  (retorna a imagem inteira).

Solução:
1. Classifica cada pixel como "logo" (colorido e/ou escuro) ou "fundo"
   (tons de cinza/branco do padrão de xadrez) usando saturação e brilho.
2. Limpa ruído isolado (pixels de compressão) com abertura morfológica
   (erosão + dilatação) antes de calcular o bounding box, para não capturar
   pixels espúrios distantes da logo.
3. Constrói um canal alpha real a partir dessa máscara (com um leve blur para
   suavizar as bordas) e recorta a imagem pelo bounding box desse alpha
   (Image.getbbox()/split()[-1].getbbox()), agora sim sobre transparência real.
4. Cola o recorte centralizado em um canvas QUADRADO transparente (lado =
   maior dimensão do recorte + padding de 10%), preservando a proporção.
5. Redimensiona esse canvas quadrado para cada tamanho final com LANCZOS.
"""

import os
import sys

import numpy as np
from PIL import Image, ImageFilter

CON_STR_INPUT_PATH = "Gemini_Generated_Image_4958qo4958qo4958.png"
CON_STR_OUTPUT_DIR = "extension/icons"
CON_STR_OUTPUT_DIR_DARK = "extension/icons/dark"
CON_LIST_SIZES = [16, 48, 128]
CON_FLOAT_PADDING_PCT = 0.10  # 10% de margem ao redor da logo no canvas quadrado
CON_TUPLE_COR_CLARA = (232, 238, 245)  # cor que substitui o azul-marinho na variante para tema escuro


def _construir_alpha_real(arg_imgRgb: Image.Image) -> Image.Image:
    """
    Deriva um canal alpha real (transparência) a partir de uma imagem cujo
    "fundo transparente" foi, na verdade, rasterizado como um padrão de
    xadrez cinza/branco (sem transparência de fato).

    Parâmetros:
    - arg_imgRgb (Image.Image): Imagem fonte em modo RGB.

    Retorna:
    - Image.Image: Imagem em modo "L" com o canal alpha derivado (255 = logo,
      0 = fundo), já limpo de ruído e com bordas levemente suavizadas.
    """
    var_arrImagem = np.array(arg_imgRgb).astype(int)
    var_arrR, var_arrG, var_arrB = var_arrImagem[..., 0], var_arrImagem[..., 1], var_arrImagem[..., 2]

    var_arrMax = np.maximum(np.maximum(var_arrR, var_arrG), var_arrB)
    var_arrMin = np.minimum(np.minimum(var_arrR, var_arrG), var_arrB)
    var_arrSaturacao = var_arrMax - var_arrMin
    var_arrBrilho = (var_arrR + var_arrG + var_arrB) / 3.0

    # Pontuação de "conteúdo de logo": alta saturação (cores) OU baixo brilho
    # (traços escuros/contornos). O fundo em xadrez é sempre acinzentado
    # (saturação baixa) e claro (brilho alto), então fica com pontuação ~0.
    var_arrPontuacao = np.maximum(var_arrSaturacao.astype(float) - 15, (180 - var_arrBrilho))
    var_arrPontuacao = np.clip(var_arrPontuacao, 0, 60) / 60.0
    var_arrAlphaBruto = (var_arrPontuacao * 255).astype(np.uint8)
    var_imgAlphaBruto = Image.fromarray(var_arrAlphaBruto, mode="L")

    # Binariza e remove ruído isolado (abertura morfológica) para que pixels
    # espúrios de compressão, distantes da logo, não distorçam o bounding box.
    var_imgBinario = var_imgAlphaBruto.point(lambda arg_intPixel: 255 if arg_intPixel > 40 else 0)
    var_imgLimpo = var_imgBinario.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))

    # Dilata levemente a máscara limpa para não cortar as bordas com
    # anti-aliasing (que têm pontuação de alpha mais baixa que 255).
    var_imgMascaraDilatada = var_imgLimpo.filter(ImageFilter.MaxFilter(5))
    var_arrMascara = np.array(var_imgMascaraDilatada) > 0

    var_arrAlphaFinal = np.where(var_arrMascara, var_arrAlphaBruto, 0).astype(np.uint8)
    var_imgAlphaFinal = Image.fromarray(var_arrAlphaFinal, mode="L").filter(ImageFilter.GaussianBlur(radius=1.0))

    return var_imgAlphaFinal


def _gerar_variante_tema_escuro(arg_imgCanvasRgba: Image.Image) -> Image.Image:
    """
    Deriva a variante do ícone usada quando a toolbar do navegador está no
    tema escuro: o traço azul-marinho do logo (baixo contraste sobre fundo
    escuro) é clareado, mantendo o laranja e o verde como estão, já que
    ambos contrastam bem tanto em fundos claros quanto escuros.

    Parâmetros:
    - arg_imgCanvasRgba (Image.Image): canvas quadrado RGBA (variante clara).

    Retorna:
    - Image.Image: canvas RGBA equivalente com o azul-marinho clareado.
    """
    var_arrImagem = np.array(arg_imgCanvasRgba).astype(float)
    var_arrR, var_arrG, var_arrB = var_arrImagem[..., 0], var_arrImagem[..., 1], var_arrImagem[..., 2]

    # "Azul-marinho-idade": quanto mais o azul domina sobre vermelho/verde e
    # quanto mais escuro o pixel, mais ele deve ser puxado para a cor clara.
    var_arrDominanciaAzul = np.clip((var_arrB - np.maximum(var_arrR, var_arrG)) / 40.0, 0, 1)
    var_arrEscuridao = np.clip((140 - np.maximum(np.maximum(var_arrR, var_arrG), var_arrB)) / 60.0, 0, 1)
    var_arrPeso = np.clip(var_arrDominanciaAzul * var_arrEscuridao, 0, 1)[..., None]

    var_arrCorClara = np.array(CON_TUPLE_COR_CLARA, dtype=float)
    var_arrRgbFinal = var_arrImagem[..., :3] * (1 - var_arrPeso) + var_arrCorClara * var_arrPeso

    var_arrSaida = np.dstack([var_arrRgbFinal, var_arrImagem[..., 3]]).astype(np.uint8)
    return Image.fromarray(var_arrSaida, mode="RGBA")


def gerar_icones() -> None:
    """Gera os ícones da extensão a partir da imagem-fonte, sem distorção."""
    try:
        var_imgEntrada = Image.open(CON_STR_INPUT_PATH)
    except Exception as arg_objErro:
        print(f"Error opening image: {arg_objErro}")
        sys.exit(1)

    var_imgRgb = var_imgEntrada.convert("RGB")
    var_imgAlpha = _construir_alpha_real(var_imgRgb)

    var_imgRgba = var_imgRgb.convert("RGBA")
    var_imgRgba.putalpha(var_imgAlpha)

    # 1. Bounding box do conteúdo não-transparente (agora sobre alpha real).
    var_tupleBbox = var_imgRgba.split()[-1].getbbox()
    if var_tupleBbox is None:
        print("Nenhum conteúdo detectado na imagem-fonte (alpha vazio).")
        sys.exit(1)

    # 2. Recorta para o bounding box.
    var_imgRecortada = var_imgRgba.crop(var_tupleBbox)

    # 3. Cola centralizado em um canvas quadrado transparente, com padding,
    #    preservando a proporção original (sem distorcer).
    var_intLadoConteudo = max(var_imgRecortada.size)
    var_intPadding = int(var_intLadoConteudo * CON_FLOAT_PADDING_PCT)
    var_intLadoCanvas = var_intLadoConteudo + var_intPadding * 2

    var_imgCanvas = Image.new("RGBA", (var_intLadoCanvas, var_intLadoCanvas), (0, 0, 0, 0))
    var_tupleOffset = (
        (var_intLadoCanvas - var_imgRecortada.size[0]) // 2,
        (var_intLadoCanvas - var_imgRecortada.size[1]) // 2,
    )
    var_imgCanvas.paste(var_imgRecortada, var_tupleOffset, var_imgRecortada)

    # 5. Deriva a variante para tema escuro (mesmo recorte, azul-marinho clareado).
    var_imgCanvasEscuro = _gerar_variante_tema_escuro(var_imgCanvas)

    os.makedirs(CON_STR_OUTPUT_DIR, exist_ok=True)
    os.makedirs(CON_STR_OUTPUT_DIR_DARK, exist_ok=True)

    # 6. Redimensiona os dois canvases quadrados (proporção 1:1) para cada tamanho final.
    for var_intSize in CON_LIST_SIZES:
        var_imgRedimensionada = var_imgCanvas.resize((var_intSize, var_intSize), Image.Resampling.LANCZOS)
        var_strOutputPath = os.path.join(CON_STR_OUTPUT_DIR, f"icon{var_intSize}.png")
        var_imgRedimensionada.save(var_strOutputPath, "PNG")
        print(f"Saved {var_strOutputPath}")

        var_imgRedimensionadaEscuro = var_imgCanvasEscuro.resize((var_intSize, var_intSize), Image.Resampling.LANCZOS)
        var_strOutputPathEscuro = os.path.join(CON_STR_OUTPUT_DIR_DARK, f"icon{var_intSize}.png")
        var_imgRedimensionadaEscuro.save(var_strOutputPathEscuro, "PNG")
        print(f"Saved {var_strOutputPathEscuro}")

    print("Done!")


if __name__ == "__main__":
    gerar_icones()
