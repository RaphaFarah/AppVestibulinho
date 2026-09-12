# -*- coding: utf-8 -*-
"""Primitivas de extracao: ordena linhas de texto respeitando faixas e colunas."""
import re
import pymupdf

GAP_FULLWIDTH = 0.62   # fracao da largura para considerar bloco "full width"
EDGE = 12              # tolerancia em pontos


def _lines_of(page):
    out = []
    d = page.get_text("dict")
    for blk in d["blocks"]:
        if blk.get("type") != 0:
            continue
        for ln in blk["lines"]:
            txt = "".join(sp["text"] for sp in ln["spans"])
            if not txt.strip():
                continue
            x0, y0, x1, y1 = ln["bbox"]
            sizes = [sp["size"] for sp in ln["spans"]]
            out.append({
                "text": txt, "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                "size": round(sum(sizes) / len(sizes), 1),
            })
    return out


def ordered_lines(page):
    """Linhas em ordem de leitura: divide a pagina em faixas por blocos full-width,
    e dentro de cada faixa le coluna esquerda inteira, depois a direita."""
    W = page.rect.width
    mid = W / 2
    lines = _lines_of(page)
    if not lines:
        return []

    full = [l for l in lines if (l["x1"] - l["x0"]) > W * GAP_FULLWIDTH
            or (l["x0"] < mid - EDGE and l["x1"] > mid + EDGE)]
    narrow = [l for l in lines if l not in full]

    if not narrow:
        # pagina sem colunas: tudo em ordem vertical, tratado como coluna 0
        out = sorted(lines, key=lambda l: (l["y0"], l["x0"]))
        for l in out:
            l["col"] = 0
        return out

    # fronteiras de faixa = y dos blocos full-width
    bounds = sorted(set([0.0] + [l["y0"] for l in full] + [page.rect.height]))
    bands = []
    for i in range(len(bounds) - 1):
        top, bot = bounds[i], bounds[i + 1]
        inb = [l for l in narrow if top <= l["y0"] < bot]
        fw = [l for l in full if abs(l["y0"] - top) < 0.01]
        bands.append((fw, inb))

    out = []
    for fw, inb in bands:
        out.extend(sorted(fw, key=lambda l: (l["y0"], l["x0"])))
        left = [l for l in inb if (l["x0"] + l["x1"]) / 2 < mid]
        right = [l for l in inb if (l["x0"] + l["x1"]) / 2 >= mid]
        out.extend(sorted(left, key=lambda l: l["y0"]))
        out.extend(sorted(right, key=lambda l: l["y0"]))
    for l in out:
        l["col"] = 0 if (l["x0"] + l["x1"]) / 2 < mid else 1
    return out


def doc_lines(path):
    """Todas as linhas do documento, com numero de pagina."""
    doc = pymupdf.open(path)
    res = []
    for pno in range(doc.page_count):
        page = doc[pno]
        for l in ordered_lines(page):
            l["page"] = pno
            res.append(l)
    doc.close()
    return res


def dehyphenate(text):
    """Junta palavras quebradas por hifen no fim de linha."""
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return text
