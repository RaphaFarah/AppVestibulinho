# -*- coding: utf-8 -*-
"""Monta o payload estático que o PWA baixa e cacheia: web/public/dados/.

O app roda o simulado offline, então o banco de questões vai inteiro para o
cliente -- um único JSON em vez de 13, para ser uma requisição e um cache.
Questão pendente de revisão e questão anulada ficam fora, como no SQLite.

Uso:
    python tools/build_web.py
"""
import os
import re
import json
import glob
import shutil
import hashlib
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_DIR = os.path.join(ROOT, "data", "questoes")
IMG_DIR = os.path.join(ROOT, "data", "imagens")
SAIDA = os.path.join(ROOT, "web", "public", "dados")

AREA = {
    "Língua Portuguesa": "Linguagens",
    "Inglês": "Linguagens",
    "Matemática": "Matemática",
    "Ciências": "Ciências Naturais",
    "Ciências Naturais": "Ciências Naturais",
    "História": "Ciências Humanas",
    "Geografia": "Ciências Humanas",
    "Ciências Humanas": "Ciências Humanas",
}


def caminho_web(arquivo):
    """'data/imagens/2022/x.png' -> 'imagens/2022/x.png' (relativo ao payload)."""
    return re.sub(r"^data/imagens/", "imagens/", arquivo)


def main():
    os.makedirs(SAIDA, exist_ok=True)
    questoes, contextos, usadas = [], {}, set()
    fora = {"revisar": 0, "anulada": 0}

    for caminho in sorted(glob.glob(os.path.join(JSON_DIR, "*.json"))):
        d = json.load(open(caminho, encoding="utf-8"))
        ano = d["ano"]
        por_id = {c["id"]: c for c in d["contextos"]}

        for q in d["questoes"]:
            if q["revisar"]:
                fora["revisar"] += 1
                continue
            if q["anulada"]:
                fora["anulada"] += 1
                continue

            figs = [caminho_web(f["arquivo"]) for f in q["figuras"]]
            alts = [{"letra": a["letra"], "texto": a["texto"] or None,
                     "figura": caminho_web(a["figura"]["arquivo"]) if a["figura"] else None}
                    for a in q["alternativas"]]
            usadas.update(figs)
            usadas.update(a["figura"] for a in alts if a["figura"])

            if q["contexto_id"] and q["contexto_id"] not in contextos:
                c = por_id.get(q["contexto_id"])
                if c:
                    cfigs = [caminho_web(f["arquivo"]) for f in c["figuras"]]
                    usadas.update(cfigs)
                    contextos[c["id"]] = {
                        "id": c["id"], "instrucao": c["instrucao"],
                        "texto": c["texto"],
                        "textoNaFigura": c["texto_na_figura"],
                        "figuras": cfigs}

            questoes.append({
                "id": f"{ano}-q{q['numero']:02d}",
                "ano": ano, "numero": q["numero"],
                "materia": q["materia"], "area": AREA.get(q["materia"]),
                "contextoId": q["contexto_id"],
                "enunciado": q["enunciado"],
                "alternativas": alts,
                "correta": q["correta"],
                "figuras": figs,
            })

    banco = {
        "versao": date.today().isoformat(),
        "questoes": questoes,
        "contextos": contextos,
    }
    destino = os.path.join(SAIDA, "banco.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(banco, f, ensure_ascii=False, separators=(",", ":"))

    # copia apenas as imagens realmente referenciadas
    copiadas = 0
    for rel in sorted(usadas):
        orig = os.path.join(ROOT, "data", rel.replace("/", os.sep))
        dest = os.path.join(SAIDA, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if not os.path.exists(dest) or os.path.getmtime(orig) > os.path.getmtime(dest):
            shutil.copy2(orig, dest)
        copiadas += 1

    tam = os.path.getsize(destino) / 1024
    digest = hashlib.sha256(open(destino, "rb").read()).hexdigest()[:12]
    por_area = {}
    for q in questoes:
        por_area[q["area"]] = por_area.get(q["area"], 0) + 1

    print(f"{destino}  ({tam:.0f} KB, sha256 {digest})")
    print(f"  questoes ....... {len(questoes)}")
    for area, n in sorted(por_area.items(), key=lambda x: -x[1]):
        print(f"      {area:<18} {n:>3}")
    print(f"  contextos ...... {len(contextos)}")
    print(f"  imagens ........ {copiadas}")
    print(f"  fora do payload  revisar={fora['revisar']} anulada={fora['anulada']}")


if __name__ == "__main__":
    main()
