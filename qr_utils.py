"""
Geracao de imagens de QR Code com degrade de cores personalizado, logo
central, borda colorida e texto de chamada acima da imagem, alem da
conversao para os formatos de exportacao (PNG, JPG, PDF).
"""
import io
import os

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import (
    HorizontalGradiantColorMask,
    VerticalGradiantColorMask,
    RadialGradiantColorMask,
    SquareGradiantColorMask,
)
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageOps

LOGO_SIZE = 300  # tamanho (em pixels) do quadrado usado para padronizar o logo enviado

# Fonte usada no texto de chamada (ex: "Aponte a câmera"). Usamos um arquivo
# TTF proprio (DejaVu Sans, licença livre) em vez da fonte padrão do Pillow,
# porque a padrão não desenha corretamente acentos/cedilha do português.
_FONT_PATH = os.path.join(os.path.dirname(__file__), "static", "fonts", "DejaVuSans-Bold.ttf")


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(_FONT_PATH, size)
    except OSError:
        # Se por algum motivo o arquivo de fonte não estiver disponível,
        # usa a fonte padrão do Pillow (não desenha acentos corretamente,
        # mas evita que a geração do QR Code quebre).
        return ImageFont.load_default(size=size)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = (hex_color or "#FFFFFF").lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def build_color_mask(color_start: str, color_end: str, direction: str):
    start = _hex_to_rgb(color_start)
    end = _hex_to_rgb(color_end)
    white = (255, 255, 255)

    if direction == "vertical":
        return VerticalGradiantColorMask(back_color=white, top_color=start, bottom_color=end)
    if direction == "radial":
        return RadialGradiantColorMask(back_color=white, center_color=start, edge_color=end)
    if direction == "square":
        return SquareGradiantColorMask(back_color=white, center_color=start, edge_color=end)
    # default: horizontal
    return HorizontalGradiantColorMask(back_color=white, left_color=start, right_color=end)


def generate_qr_image(
    data: str,
    color_start: str,
    color_end: str,
    direction: str,
    logo_path: str | None = None,
) -> Image.Image:
    """Gera a imagem (Pillow) do QR Code com o degrade escolhido e, se
    informado, um logo centralizado (error correction alto para manter a
    leitura mesmo com a area central coberta)."""
    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    color_mask = build_color_mask(color_start, color_end, direction)

    kwargs = dict(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=color_mask,
    )
    if logo_path:
        kwargs["embeded_image_path"] = logo_path

    img = qr.make_image(**kwargs)
    return img.convert("RGB")


def resize_logo_to_square(image: Image.Image, size: int = LOGO_SIZE) -> Image.Image:
    """Padroniza um logo enviado pelo usuario para um quadrado size x size,
    mantendo a proporcao original (encaixa e centraliza em fundo transparente)."""
    image = image.convert("RGBA")
    image.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    offset = ((size - image.width) // 2, (size - image.height) // 2)
    canvas.paste(image, offset, image)
    return canvas


def _fit_caption_lines(draw: ImageDraw.ImageDraw, text: str, max_width: int) -> tuple[list[str], ImageFont.FreeTypeFont]:
    """Escolhe um tamanho de fonte e, se necessario, quebra o texto em mais
    de uma linha, para que a legenda sempre caiba dentro de max_width."""
    font_size = 30
    min_font_size = 14

    while font_size >= min_font_size:
        font = _load_font(font_size)
        width = draw.textbbox((0, 0), text, font=font)[2]
        if width <= max_width:
            return [text], font
        font_size -= 2

    # Ainda nao coube nem no menor tamanho: quebra em varias linhas.
    font = _load_font(min_font_size)
    avg_char_width = max(1, draw.textbbox((0, 0), text, font=font)[2] // max(1, len(text)))
    chars_per_line = max(10, max_width // avg_char_width)
    lines = textwrap.wrap(text, width=chars_per_line) or [text]
    return lines, font


def add_border_and_caption(
    img: Image.Image,
    border_color: str,
    caption_text: str | None,
    border_thickness: int = 18,
) -> Image.Image:
    """Adiciona uma borda colorida ao redor do QR Code e, opcionalmente, um
    texto centralizado acima dele (ex: "Aponte a camera"), quebrando em
    varias linhas ou diminuindo a fonte automaticamente se o texto for
    longo demais para a largura do QR Code."""
    bordered = ImageOps.expand(img, border=border_thickness, fill=_hex_to_rgb(border_color))

    caption_text = (caption_text or "").strip()
    if not caption_text:
        return bordered

    width, height = bordered.size
    padding = 20
    max_text_width = width - (padding * 2)

    dummy = ImageDraw.Draw(bordered)
    lines, font = _fit_caption_lines(dummy, caption_text, max_text_width)

    line_bbox = dummy.textbbox((0, 0), "Ag", font=font)
    line_height = (line_bbox[3] - line_bbox[1]) + 8
    caption_area = (line_height * len(lines)) + 24

    final_img = Image.new("RGB", (width, height + caption_area), "white")
    draw = ImageDraw.Draw(final_img)

    y = (caption_area - line_height * len(lines)) // 2
    for line in lines:
        line_width = draw.textbbox((0, 0), line, font=font)[2]
        x = max(padding, (width - line_width) // 2)
        draw.text((x, y), line, font=font, fill=(15, 23, 42))
        y += line_height

    final_img.paste(bordered, (0, caption_area))
    return final_img


def image_to_bytes(img: Image.Image, fmt: str) -> bytes:
    """Converte a imagem Pillow para bytes no formato pedido: PNG, JPEG ou PDF."""
    buffer = io.BytesIO()
    fmt = fmt.upper()
    if fmt == "JPG":
        fmt = "JPEG"

    if fmt == "JPEG":
        # fundo branco, pois JPEG nao tem transparencia
        rgb_img = img.convert("RGB")
        rgb_img.save(buffer, format="JPEG", quality=95)
    elif fmt == "PDF":
        img.convert("RGB").save(buffer, format="PDF")
    else:
        img.save(buffer, format="PNG")

    buffer.seek(0)
    return buffer.read()
