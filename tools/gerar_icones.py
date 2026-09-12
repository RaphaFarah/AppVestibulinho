# -*- coding: utf-8 -*-
"""Gera os ícones do PWA em web/public/. Sem eles o app não é instalável.

Uso:
    python tools/gerar_icones.py
"""
import os

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(ROOT, "web", "public")

AZUL = (0.122, 0.373, 0.816)   # --realce do tema
BRANCO = (1, 1, 1)


def desenhar(lado: int, nome: str, margem: float = 0.0):
    """margem > 0 deixa área de respiro para ícone 'maskable' (recorte circular)."""
    doc = pymupdf.open()
    pagina = doc.new_page(width=lado, height=lado)
    pagina.draw_rect(pymupdf.Rect(0, 0, lado, lado), color=None, fill=AZUL)

    # "V" de Vestibulinho, centralizado
    corpo = lado * (1 - 2 * margem)
    tamanho = corpo * 0.62
    pagina.insert_text(
        pymupdf.Point(lado / 2 - tamanho * 0.33, lado / 2 + tamanho * 0.36),
        "V", fontsize=tamanho, fontname="hebo", color=BRANCO,
    )
    caminho = os.path.join(SAIDA, nome)
    # a pagina ja tem o lado exato em pontos, logo escala 1 = lado em pixels
    pagina.get_pixmap(alpha=False).save(caminho)
    doc.close()
    return caminho


if __name__ == "__main__":
    os.makedirs(SAIDA, exist_ok=True)
    for lado, nome, margem in (
        (192, "icone-192.png", 0.0),
        (512, "icone-512.png", 0.0),
        (512, "icone-maskable-512.png", 0.12),
        (180, "apple-touch-icon.png", 0.0),
        (64, "favicon.png", 0.0),
    ):
        print(desenhar(lado, nome, margem))
