# -*- coding: utf-8 -*-
"""Extrai questoes, alternativas, gabarito e figuras das provas em PDF -> JSON + PNG.

Uso:
    python tools/parse_exam.py                 # todos os anos
    python tools/parse_exam.py 2022 2008       # anos escolhidos
    python tools/parse_exam.py --sem-imagens   # so o JSON, sem renderizar PNG
    python tools/parse_exam.py --integral-tudo # recorte integral de toda questao
"""
import os
import re
import sys
import json
import unicodedata
import argparse
import difflib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfio import ordered_lines
from sources import SRC, PROVAS, MATERIA_CANON

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, "data", "questoes")
OUT_IMG = os.path.join(ROOT, "data", "imagens")

RE_Q_NUM = re.compile(r"^\s*0?(\d{1,2})\.\s+(\S.*)$")
RE_Q_MARK = re.compile(r"^\s*QUESTÃO\s*0?(\d{1,2})\s*$", re.I)
RE_ALT = re.compile(r"^\s*\(([A-E])\)\s*(.*)$")
RE_GAB = re.compile(r"(\d{1,2})\s*[-–—]\s*([A-EN])")   # N = questao anulada
RE_SHARED = re.compile(
    r"questões?\s*(?:de\s*números?)?\s*(\d{1,2})\s*(a|e|até)\s*(\d{1,2})", re.I)
# enunciado com formula inline perdida: "= ," / "= e" / termina em "="
RE_FORMULA_PERDIDA = re.compile(r"=\s*[,.]|=\s+e\s|=\s*$|\s{3,}")

MIN_BAND_H = 22.0      # altura minima (pt) de uma faixa para valer como figura
BRIDGE = 9.0           # une intervalos de desenho separados por menos que isto
DPI = 200
DPI_INTEGRAL = 150


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


_CAND = {strip_accents(k).lower(): v for k, v in MATERIA_CANON.items()}


def materia_de(texto):
    """Se a linha for um cabecalho de materia, devolve o nome canonico.

    Aceita MAIUSCULAS (provas antigas) e Title Case (provas novas), e tolera
    erro de digitacao do PDF original ('Lingua Portugesa' em 2021, 'Cencias
    Humanas' em 2021). Rejeita fragmento de frase, que termina em ponto."""
    t = texto.strip()
    if not t or len(t) > 45 or t.endswith("."):
        return None
    key = re.sub(r"\s+", " ", strip_accents(t)).strip().lower()
    if key in _CAND:
        return _CAND[key]
    perto = difflib.get_close_matches(key, list(_CAND), n=1, cutoff=0.90)
    return _CAND[perto[0]] if perto else None


def eh_mobilia(texto, no_rodape=False):
    """Rodape, marca d'agua e folha de rascunho -- nunca fazem parte da questao.

    Numero solto so conta como numero de pagina se estiver no rodape: em
    Matematica o numerador e o denominador de uma fracao saem como linhas
    separadas, e '3' sozinho no meio da coluna e conteudo, nao mobiliario."""
    s = re.sub(r"\s+", "", strip_accents(texto)).upper()
    if not s:
        return False
    if s.startswith("RASCUNHO") or "CTIN" in s or "CONFIDENCIAL" in s:
        return True
    if "VESTIBULINHO" in s and len(s) < 60:
        return True
    if no_rodape and re.fullmatch(r"\d{1,3}", s):
        return True
    return False


def col_bounds(page, lines, col):
    """Extensao horizontal ocupada pelo texto de uma coluna."""
    mid = page.rect.width / 2
    xs = [(l["x0"], l["x1"]) for l in lines if l["col"] == col]
    if xs:
        return min(a for a, _ in xs), max(b for _, b in xs)
    return (0.0, mid) if col == 0 else (mid, page.rect.width)


def _merge(iv, bridge=BRIDGE):
    if not iv:
        return []
    iv = sorted(iv)
    out = [list(iv[0])]
    for a, b in iv[1:]:
        if a - out[-1][1] <= bridge:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def figure_bands(page, x0, x1):
    """Faixas verticais que contem figura de verdade dentro da coluna [x0,x1].

    Traco fino isolado nao conta: o separador vertical de colunas e os fiozinhos
    decorativos do rotulo QUESTAO sao mobiliario de pagina, nao figura. Formas 2D
    e imagens valem por si; tracos finos so valem em grupo de 3+ (grade de tabela)."""
    W, H = page.rect.width, page.rect.height
    solidos, tracos = [], []
    for d in page.get_drawings():
        r = d["rect"]
        cx = (r.x0 + r.x1) / 2
        if cx < x0 - 12 or cx > x1 + 12:
            continue                                   # pertence a outra coluna
        if r.width > W * 0.85 and r.height > H * 0.85:
            continue                                   # moldura da pagina
        fino = r.width <= 3.0 or r.height <= 3.0
        if not fino:
            solidos.append([r.y0, r.y1])
        elif r.width <= 2.5 and r.height > 150:
            continue                                   # separador vertical
        elif max(r.width, r.height) >= 15:
            tracos.append([r.y0, r.y1])

    for blk in page.get_text("dict")["blocks"]:
        if blk.get("type") == 1:                       # imagem rasterizada
            bx0, by0, bx1, by1 = blk["bbox"]
            cx = (bx0 + bx1) / 2
            if x0 - 12 <= cx <= x1 + 12:
                solidos.append([by0, by1])

    grades = []
    for grupo in _merge(tracos, bridge=30.0):
        dentro = [t for t in tracos if grupo[0] <= t[0] <= grupo[1]]
        if len(dentro) >= 3 and (grupo[1] - grupo[0]) >= 20:
            grades.append(grupo)

    return [(a, b) for a, b in _merge(solidos + grades) if (b - a) >= MIN_BAND_H]


def in_band(line, bands):
    return any(y0 - 2 <= line["y0"] and line["y1"] <= y1 + 2 for y0, y1 in bands)


INVISIVEIS = str.maketrans({"­": "", "​": "", "‌": "",
                            "‍": "", "﻿": "", " ": " "})


def join(parts):
    """Junta linhas resolvendo hifenizacao de fim de linha.

    Remove tambem hifen opcional e espaco fixo, que o PDF usa para justificar
    o texto e que vazam invisiveis para dentro das palavras."""
    buf = ""
    for p in parts:
        p = re.sub(r"\s+", " ", p.translate(INVISIVEIS).replace("\t", " ")).strip()
        if not p:
            continue
        if buf.endswith("-") and p[:1].islower():
            buf = buf[:-1] + p
        elif buf:
            buf += " " + p
        else:
            buf = p
    return buf.strip()


def span_of(lines):
    """Mapa (pagina, coluna) -> (y inicial, y final) ocupado pelas linhas."""
    segs = {}
    for l in lines:
        key = (l["page"], l["col"])
        y0, y1 = segs.get(key, (l["y0"], l["y1"]))
        segs[key] = (min(y0, l["y0"]), max(y1, l["y1"]))
    return segs


def load_gabarito(path, nq=50):
    """Devolve {numero: letra} -- 'N' no PDF significa questao anulada."""
    doc = pymupdf.open(path)
    txt = "".join(p.get_text() for p in doc)
    doc.close()
    gab = {}
    for n, letra in RE_GAB.findall(txt):
        n = int(n)
        if 1 <= n <= nq and n not in gab:
            gab[n] = letra
    return gab


def parse(ano, render=True, integral_tudo=False):
    meta = PROVAS[ano]
    doc = pymupdf.open(os.path.join(SRC, meta["prova"]))
    destino = os.path.join(OUT_IMG, str(ano))
    if render:
        os.makedirs(destino, exist_ok=True)

    # ---- 1. fluxo linear de linhas + faixas de figura por (pagina, coluna)
    stream, bands, bounds, alturas, desenhos = [], {}, {}, {}, {}
    for pno in range(doc.page_count):
        page = doc[pno]
        alturas[pno] = page.rect.height
        lines = ordered_lines(page)
        W, H = page.rect.width, page.rect.height
        for col in (0, 1):
            x0, x1 = col_bounds(page, lines, col)
            bounds[(pno, col)] = (x0, x1)
            bands[(pno, col)] = figure_bands(page, x0, x1)
            reg = []
            for d in page.get_drawings():
                r = d["rect"]
                cx = (r.x0 + r.x1) / 2
                if cx < x0 - 12 or cx > x1 + 12:
                    continue
                if r.width > W * 0.85 and r.height > H * 0.85:
                    continue                           # moldura da pagina
                if r.width <= 2.5 and r.height > 150:
                    continue                           # separador vertical
                reg.append((r.y0, r.y1))
            desenhos[(pno, col)] = reg
        for l in lines:
            l["page"] = pno
            stream.append(l)
    ultimo = len(stream)

    def estende(pno, col, y0, y1, limite=45.0):
        """Estica o recorte para cobrir desenho que desce abaixo do texto.

        Fracao, raiz e expoente sao desenhados fora da caixa da linha de texto:
        sem isto o recorte corta a alternativa (D) no meio."""
        ny0, ny1 = y0, y1
        for dy0, dy1 in desenhos.get((pno, col), []):
            if dy0 < y1 + 8 and dy1 > y0 - 8:
                ny0, ny1 = min(ny0, dy0), max(ny1, dy1)
        return max(ny0, y0 - limite), min(ny1, y1 + limite)

    def recorta(pno, rect, nome, dpi=DPI):
        """Salva um recorte da pagina como PNG e devolve o registro."""
        page = doc[pno]
        clip = pymupdf.Rect(max(0.0, rect[0]), max(0.0, rect[1]),
                            min(page.rect.width, rect[2]),
                            min(page.rect.height, rect[3]))
        if render and clip.width > 4 and clip.height > 4:
            page.get_pixmap(clip=clip, dpi=dpi).save(os.path.join(destino, nome))
        return dict(arquivo=f"data/imagens/{ano}/{nome}", pagina=pno + 1)

    def figuras_em(segs, prefix):
        """Faixas de figura que intersectam os trechos (pagina, coluna) dados."""
        figs = []
        for (pno, col), (qy0, qy1) in sorted(segs.items()):
            for bi, (by0, by1) in enumerate(bands.get((pno, col), [])):
                if by1 < qy0 - 2 or by0 > qy1 + 2:
                    continue
                x0, x1 = bounds[(pno, col)]
                figs.append(recorta(pno, (x0 - 6, by0 - 6, x1 + 6, by1 + 6),
                                    f"{prefix}-p{pno}-c{col}-{bi}.png"))
        return figs

    # ---- 2. materia vigente em cada ponto do fluxo
    materia_em, atual = [], None
    for l in stream:
        m = materia_de(l["text"])
        if m:
            atual = m
        materia_em.append(atual)

    # ---- 3. marcadores de questao (sequencia monotonica 1..50)
    rx = RE_Q_MARK if meta["dialeto"] == "questao" else RE_Q_NUM
    marks, esperado = [], 1
    for i, l in enumerate(stream):
        if l["page"] == 0:
            continue
        m = rx.match(l["text"])
        if m and int(m.group(1)) == esperado:
            marks.append((i, esperado, m.group(2) if meta["dialeto"] == "num" else ""))
            esperado += 1

    # ---- 4. contextos (enunciados compartilhados por varias questoes)
    contextos, ctx_de = [], {}
    for i, l in enumerate(stream):
        m = RE_SHARED.search(l["text"])
        if not m or "responder" not in l["text"].lower():
            continue
        a, conector, b = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        alvo = [q for q in ([a, b] if conector == "e" else range(a, b + 1)) if 1 <= q <= 50]
        if not alvo:
            continue
        prox = next((mi for mi, _, _ in marks if mi > i), ultimo)
        trecho = stream[i + 1:prox]
        corpo = [x for x in trecho if not in_band(x, bands.get((x["page"], x["col"]), []))]
        figl = [x for x in trecho if in_band(x, bands.get((x["page"], x["col"]), []))]
        cid = f"ctx-{ano}-{a:02d}"
        contextos.append(dict(
            id=cid, questoes=alvo, instrucao=l["text"].strip(),
            texto=join([c["text"] for c in corpo]),
            texto_na_figura=join([f["text"] for f in figl]) or None,
            figuras=figuras_em(span_of(trecho), cid)))
        for q in alvo:
            ctx_de[q] = cid

    # ---- 5. questoes
    questoes = []
    for k, (idx, num, resto) in enumerate(marks):
        fim = marks[k + 1][0] if k + 1 < len(marks) else ultimo
        bloco = stream[idx:fim]
        # corta mobiliario de pagina, mas so depois que todas as alternativas
        # esperadas ja apareceram -- antes disso qualquer linha e conteudo
        rotulos = [j for j, l in enumerate(bloco) if RE_ALT.match(l["text"])]
        if len(rotulos) >= meta["alts"]:
            for j in range(rotulos[meta["alts"] - 1] + 1, len(bloco)):
                l = bloco[j]
                no_rodape = l["y0"] > alturas[l["page"]] * 0.93
                if (eh_mobilia(l["text"], no_rodape) or materia_de(l["text"])
                        or ("responder" in l["text"].lower() and RE_SHARED.search(l["text"]))):
                    bloco = bloco[:j]
                    break

        primeira_alt = next((j for j, l in enumerate(bloco) if RE_ALT.match(l["text"])),
                            len(bloco))
        linhas_enun = bloco[1:primeira_alt]
        # o enunciado conserva todo o texto: em Matematica a formula fica
        # intercalada com a frase, e recortar arrancaria parte do enunciado
        enun = join(([resto] if resto else []) + [l["text"] for l in linhas_enun])
        na_fig = join([l["text"] for l in linhas_enun
                       if in_band(l, bands.get((l["page"], l["col"]), []))])

        # alternativas, guardando as linhas para poder recortar as que sao figura
        alts, ordem = {}, []
        corrente = None
        for l in bloco[primeira_alt:]:
            m = RE_ALT.match(l["text"])
            if m:
                corrente = m.group(1)
                if corrente not in alts:
                    ordem.append(corrente)
                    alts[corrente] = dict(textos=[m.group(2)], linhas=[l])
                else:
                    alts[corrente]["textos"].append(m.group(2))
                    alts[corrente]["linhas"].append(l)
            elif corrente:
                alts[corrente]["textos"].append(l["text"])
                alts[corrente]["linhas"].append(l)

        alternativas = []
        for pos, letra in enumerate(ordem):
            texto = join(alts[letra]["textos"])
            fig = None
            if not texto:
                # alternativa e uma formula/grafico vetorial: recorta a regiao
                rot = alts[letra]["linhas"][0]
                pno, col = rot["page"], rot["col"]
                x0, x1 = bounds[(pno, col)]
                y_ini, y_fim = estende(pno, col, rot["y0"], rot["y1"])
                if pos + 1 < len(ordem):
                    prox_rot = alts[ordem[pos + 1]]["linhas"][0]
                    if (prox_rot["page"], prox_rot["col"]) == (pno, col):
                        y_fim = min(y_fim, prox_rot["y0"] - 2)
                fig = recorta(pno, (rot["x0"] - 2, y_ini - 3, x1 + 6, y_fim + 3),
                              f"{ano}-q{num:02d}-alt{letra}.png")
            alternativas.append(dict(letra=letra, texto=texto, figura=fig))

        segs = span_of(bloco)
        q = dict(numero=num, materia=materia_em[idx], contexto_id=ctx_de.get(num),
                 enunciado=enun, texto_na_figura=na_fig or None,
                 alternativas=alternativas,
                 figuras=figuras_em(segs, f"{ano}-q{num:02d}"),
                 recorte_integral=[], paginas=sorted({p + 1 for p, _ in segs}))

        # ---- por que esta questao pode precisar de conferencia humana
        motivos = []
        if len(alternativas) != meta["alts"]:
            motivos.append(f"{len(alternativas)} alternativas")
        if any(not a["texto"] and not a["figura"] for a in alternativas):
            motivos.append("alternativa vazia")
        if any(not a["texto"] and a["figura"] for a in alternativas):
            motivos.append("alternativa e figura")
        if not enun and not q["contexto_id"]:
            motivos.append("enunciado vazio")
        if RE_FORMULA_PERDIDA.search(enun):
            motivos.append("possivel formula inline perdida")
        q["revisar"] = bool(motivos)
        q["motivo_revisao"] = motivos

        # recorte integral: garantia de fidelidade onde a extracao e duvidosa
        if integral_tudo or motivos:
            for (pno, col), (qy0, qy1) in sorted(segs.items()):
                x0, x1 = bounds[(pno, col)]
                iy0, iy1 = estende(pno, col, qy0, qy1)
                q["recorte_integral"].append(
                    recorta(pno, (x0 - 6, iy0 - 6, x1 + 6, iy1 + 10),
                            f"{ano}-q{num:02d}-integral-p{pno}-c{col}.png",
                            dpi=DPI_INTEGRAL))
        questoes.append(q)

    # ---- 6. gabarito
    gab = load_gabarito(os.path.join(SRC, meta["gab"]))
    for q in questoes:
        letra = gab.get(q["numero"])
        q["anulada"] = (letra == "N")
        q["correta"] = None if q["anulada"] else letra

    doc.close()
    return dict(ano=ano, banca="Fundação Vunesp", prova="Conhecimentos Gerais",
                fonte_pdf=meta["prova"], fonte_gabarito=meta["gab"],
                n_alternativas=meta["alts"], contextos=contextos, questoes=questoes)


def validar(d):
    """Inconsistencias que impedem usar a questao numa prova simulada."""
    probs = []
    esperadas = [chr(65 + i) for i in range(d["n_alternativas"])]
    if len(d["questoes"]) != 50:
        probs.append(f"{len(d['questoes'])} questoes (esperado 50)")
    for q in d["questoes"]:
        p = []
        if [a["letra"] for a in q["alternativas"]] != esperadas:
            p.append("alts=" + "".join(a["letra"] for a in q["alternativas"]))
        if not q["correta"] and not q["anulada"]:
            p.append("sem gabarito")
        if not q["materia"]:
            p.append("sem materia")
        if not q["enunciado"] and not q["contexto_id"]:
            p.append("enunciado vazio")
        if any(not a["texto"] and not a["figura"] for a in q["alternativas"]):
            p.append("alternativa vazia")
        if p:
            probs.append(f"q{q['numero']:02d}: " + ", ".join(p))
    return probs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("anos", nargs="*", type=int)
    ap.add_argument("--sem-imagens", action="store_true")
    ap.add_argument("--integral-tudo", action="store_true")
    args = ap.parse_args()

    os.makedirs(OUT_JSON, exist_ok=True)
    total = nfig_tot = nrev = nprob = nanul = 0
    for ano in (args.anos or sorted(PROVAS)):
        d = parse(ano, render=not args.sem_imagens, integral_tudo=args.integral_tudo)
        with open(os.path.join(OUT_JSON, f"{ano}.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        nfig = (sum(len(q["figuras"]) + len(q["recorte_integral"]) for q in d["questoes"])
                + sum(len(c["figuras"]) for c in d["contextos"])
                + sum(1 for q in d["questoes"] for a in q["alternativas"] if a["figura"]))
        rev = [q["numero"] for q in d["questoes"] if q["revisar"]]
        anul = [q["numero"] for q in d["questoes"] if q["anulada"]]
        probs = validar(d)
        total += len(d["questoes"])
        nfig_tot += nfig
        nrev += len(rev)
        nprob += len(probs)
        nanul += len(anul)
        print(f"[{ano}] {len(d['questoes']):>2} questoes | {len(d['contextos'])} contextos | "
              f"{nfig:>3} imagens | revisar={rev or '-'} | anuladas={anul or '-'}")
        for p in probs:
            print("         ! " + p)
    print(f"\nTOTAL: {total} questoes, {nfig_tot} imagens, "
          f"{nrev} a revisar, {nanul} anuladas, {nprob} problemas bloqueantes")
