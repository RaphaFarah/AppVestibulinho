# -*- coding: utf-8 -*-
"""Reconhecimento dos PDFs: paginas, dimensoes, colunas, imagens e desenhos vetoriais."""
import sys, os, glob, re
import pymupdf

SRC = r"C:\Users\rapha\OneDrive\Área de Trabalho\COOTEC"

def classify_columns(page):
    """Detecta n. de colunas pela posicao horizontal dos blocos de texto."""
    w = page.rect.width
    mid = w / 2
    blocks = [b for b in page.get_text("blocks") if b[6] == 0]
    if not blocks:
        return "vazia"
    left = sum(1 for b in blocks if b[2] < mid + 10)
    right = sum(1 for b in blocks if b[0] > mid - 10)
    cross = sum(1 for b in blocks if b[0] < mid - 10 and b[2] > mid + 10)
    if left >= 2 and right >= 2 and cross <= max(1, len(blocks) // 5):
        return "2col"
    return "1col"

files = sorted(glob.glob(os.path.join(SRC, "*.pdf")))
print(f"{'arquivo':<48} {'pgs':>4} {'dimensoes':>14} {'colunas':<12} {'imgs':>5} {'vetor':>6}")
print("-" * 96)
for f in files:
    try:
        doc = pymupdf.open(f)
    except Exception as e:
        print(f"{os.path.basename(f)[:47]:<48} ERRO: {e}")
        continue
    n = doc.page_count
    p0 = doc[0]
    dims = f"{p0.rect.width:.0f}x{p0.rect.height:.0f}"
    cols = {}
    imgs = 0
    draws = 0
    for p in doc:
        cols[classify_columns(p)] = cols.get(classify_columns(p), 0) + 1
        imgs += len(p.get_images(full=True))
        draws += len(p.get_drawings())
    colstr = ",".join(f"{k}:{v}" for k, v in sorted(cols.items()))
    print(f"{os.path.basename(f)[:47]:<48} {n:>4} {dims:>14} {colstr:<12} {imgs:>5} {draws:>6}")
    doc.close()
