# -*- coding: utf-8 -*-
"""Monta data/questoes.sqlite a partir dos JSON gerados por parse_exam.py.

Uso:
    python tools/build_db.py
"""
import os
import re
import json
import glob
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_DIR = os.path.join(ROOT, "data", "questoes")
DB = os.path.join(ROOT, "data", "questoes.sqlite")
SCHEMA = os.path.join(ROOT, "tools", "schema.sql")

# As provas antigas separam Historia/Geografia/Ciencias; as novas agrupam em
# Ciencias Humanas/Naturais. O eixo comum permite sortear simulado entre anos.
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


def main():
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript(open(SCHEMA, encoding="utf-8").read())

    n_q = n_a = n_i = n_c = 0
    for caminho in sorted(glob.glob(os.path.join(JSON_DIR, "*.json"))):
        d = json.load(open(caminho, encoding="utf-8"))
        ano = d["ano"]
        con.execute(
            "INSERT INTO prova (ano, banca, prova, n_alternativas, fonte_pdf, fonte_gabarito)"
            " VALUES (?,?,?,?,?,?)",
            (ano, d["banca"], d["prova"], d["n_alternativas"],
             d["fonte_pdf"], d["fonte_gabarito"]))

        for c in d["contextos"]:
            con.execute(
                "INSERT INTO contexto (id, ano, instrucao, texto, texto_na_figura)"
                " VALUES (?,?,?,?,?)",
                (c["id"], ano, c["instrucao"], c["texto"], c["texto_na_figura"]))
            n_c += 1
            for ordem, img in enumerate(c["figuras"]):
                con.execute(
                    "INSERT INTO imagem (dono_tipo, dono_id, papel, arquivo, pagina, ordem)"
                    " VALUES ('contexto',?,'figura',?,?,?)",
                    (c["id"], img["arquivo"], img["pagina"], ordem))
                n_i += 1

        for q in d["questoes"]:
            qid = f"{ano}-q{q['numero']:02d}"
            con.execute(
                "INSERT INTO questao (id, ano, numero, materia, area, contexto_id,"
                " enunciado, texto_na_figura, correta, anulada, revisar, motivo_revisao,"
                " paginas) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (qid, ano, q["numero"], q["materia"], AREA.get(q["materia"]),
                 q["contexto_id"], q["enunciado"], q["texto_na_figura"],
                 q["correta"], int(q["anulada"]), int(q["revisar"]),
                 ", ".join(q["motivo_revisao"]) or None,
                 ",".join(str(p) for p in q["paginas"])))
            n_q += 1

            for a in q["alternativas"]:
                con.execute(
                    "INSERT INTO alternativa (questao_id, letra, texto, figura, correta)"
                    " VALUES (?,?,?,?,?)",
                    (qid, a["letra"], a["texto"] or None,
                     a["figura"]["arquivo"] if a["figura"] else None,
                     int(a["letra"] == q["correta"])))
                n_a += 1
                if a["figura"]:
                    con.execute(
                        "INSERT INTO imagem (dono_tipo, dono_id, papel, arquivo, pagina, ordem)"
                        " VALUES ('alternativa',?,'alternativa',?,?,0)",
                        (f"{qid}:{a['letra']}", a["figura"]["arquivo"],
                         a["figura"]["pagina"]))
                    n_i += 1

            for papel, lista in (("figura", q["figuras"]),
                                 ("integral", q["recorte_integral"])):
                for ordem, img in enumerate(lista):
                    con.execute(
                        "INSERT INTO imagem (dono_tipo, dono_id, papel, arquivo, pagina, ordem)"
                        " VALUES ('questao',?,?,?,?,?)",
                        (qid, papel, img["arquivo"], img["pagina"], ordem))
                    n_i += 1

    con.commit()

    # ---- busca textual, quando o SQLite tiver FTS5
    try:
        con.executescript("""
            CREATE VIRTUAL TABLE questao_fts USING fts5(
                id UNINDEXED, enunciado, alternativas, contexto,
                tokenize = 'unicode61 remove_diacritics 2');
            INSERT INTO questao_fts (id, enunciado, alternativas, contexto)
            SELECT q.id, q.enunciado,
                   (SELECT group_concat(a.texto, ' ') FROM alternativa a
                     WHERE a.questao_id = q.id),
                   COALESCE(c.texto, '')
              FROM questao q LEFT JOIN contexto c ON c.id = q.contexto_id;
        """)
        con.commit()
        fts = "sim"
    except sqlite3.OperationalError as e:
        fts = f"nao ({e})"

    tam = os.path.getsize(DB) / 1024
    print(f"{DB}  ({tam:.0f} KB)")
    print(f"  provas ......... {con.execute('SELECT COUNT(*) FROM prova').fetchone()[0]}")
    print(f"  questoes ....... {n_q}")
    print(f"  alternativas ... {n_a}")
    print(f"  contextos ...... {n_c}")
    print(f"  imagens ........ {n_i}")
    print(f"  busca textual .. {fts}")
    con.close()


if __name__ == "__main__":
    main()
