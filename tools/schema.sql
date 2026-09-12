-- Banco de questoes do Vestibulinho (Fundacao Vunesp / ETEC-COOTEC)
-- Gerado por tools/build_db.py a partir de data/questoes/*.json
PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS v_questao;
DROP TABLE IF EXISTS imagem;
DROP TABLE IF EXISTS alternativa;
DROP TABLE IF EXISTS questao;
DROP TABLE IF EXISTS contexto;
DROP TABLE IF EXISTS prova;

CREATE TABLE prova (
    ano             INTEGER PRIMARY KEY,
    banca           TEXT    NOT NULL,
    prova           TEXT    NOT NULL,
    n_alternativas  INTEGER NOT NULL,
    fonte_pdf       TEXT    NOT NULL,
    fonte_gabarito  TEXT    NOT NULL
);

-- Texto/tira/grafico compartilhado por varias questoes ("Leia o texto para
-- responder as questoes de numeros 03 a 06").
CREATE TABLE contexto (
    id               TEXT    PRIMARY KEY,
    ano              INTEGER NOT NULL REFERENCES prova(ano) ON DELETE CASCADE,
    instrucao        TEXT,
    texto            TEXT,
    texto_na_figura  TEXT            -- transcricao do que esta dentro da figura
);

CREATE TABLE questao (
    id               TEXT    PRIMARY KEY,   -- '2022-q44'
    ano              INTEGER NOT NULL REFERENCES prova(ano) ON DELETE CASCADE,
    numero           INTEGER NOT NULL,
    materia          TEXT,                  -- como impresso na prova
    area             TEXT,                  -- eixo comum entre anos
    contexto_id      TEXT    REFERENCES contexto(id) ON DELETE SET NULL,
    enunciado        TEXT    NOT NULL,
    texto_na_figura  TEXT,
    correta          TEXT    CHECK (correta IS NULL OR correta IN ('A','B','C','D','E')),
    anulada          INTEGER NOT NULL DEFAULT 0,
    revisar          INTEGER NOT NULL DEFAULT 0,
    motivo_revisao   TEXT,
    paginas          TEXT,
    UNIQUE (ano, numero)
);

CREATE TABLE alternativa (
    questao_id  TEXT    NOT NULL REFERENCES questao(id) ON DELETE CASCADE,
    letra       TEXT    NOT NULL CHECK (letra IN ('A','B','C','D','E')),
    texto       TEXT,                       -- vazio quando a alternativa e figura
    figura      TEXT,                       -- caminho do PNG, quando for figura
    correta     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (questao_id, letra)
);

-- Imagens vinculadas a questao, ao contexto ou a uma alternativa.
--   papel = 'figura'      figura publicada junto do enunciado
--   papel = 'alternativa' a propria alternativa e uma formula/grafico
--   papel = 'integral'    recorte da questao inteira, para conferencia
CREATE TABLE imagem (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    dono_tipo  TEXT    NOT NULL CHECK (dono_tipo IN ('questao','contexto','alternativa')),
    dono_id    TEXT    NOT NULL,
    papel      TEXT    NOT NULL CHECK (papel IN ('figura','alternativa','integral')),
    arquivo    TEXT    NOT NULL,
    pagina     INTEGER,
    ordem      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_questao_ano      ON questao (ano);
CREATE INDEX idx_questao_materia  ON questao (materia);
CREATE INDEX idx_questao_area     ON questao (area);
CREATE INDEX idx_questao_contexto ON questao (contexto_id);
CREATE INDEX idx_imagem_dono      ON imagem (dono_tipo, dono_id);

-- Questao pronta para montar simulado: ja traz o contexto e a contagem de imagens.
CREATE VIEW v_questao AS
SELECT q.id, q.ano, q.numero, q.materia, q.area, q.enunciado, q.correta,
       q.anulada, q.revisar,
       c.texto AS contexto_texto,
       (SELECT COUNT(*) FROM alternativa a WHERE a.questao_id = q.id) AS n_alternativas,
       (SELECT COUNT(*) FROM imagem i
         WHERE i.dono_id = q.id AND i.papel = 'figura')               AS n_figuras,
       (SELECT COUNT(*) FROM alternativa a
         WHERE a.questao_id = q.id AND a.figura IS NOT NULL)          AS n_alt_figura
FROM questao q
LEFT JOIN contexto c ON c.id = q.contexto_id;
