# AppVestibulinho

PWA de provas simuladas com questões reais do **Vestibulinho ETEC / COOTEC**
(Fundação Vunesp), extraídas das provas de Conhecimentos Gerais de 2008 a 2022.

**650 questões** de 13 provas, com gabarito, alternativas, matéria, textos
compartilhados e figuras vinculadas.

## Stack

| Camada | Escolha | Onde |
|---|---|---|
| Frontend | React + Vite + TypeScript, PWA instalável | `web/` |
| Backend | Python + FastAPI, JWT do Supabase | `api/` |
| Dados de usuário | Postgres (Supabase) | `api/schema.sql` |
| Banco de questões | JSON + PNG estáticos, servidos por CDN | `data/` |
| Extração | Python + PyMuPDF | `tools/` |

**O banco de questões não passa pela API.** Ele é estático e pequeno (598 KB de
JSON), então vai inteiro para o cliente e é cacheado pelo service worker: o
simulado roda **offline**, e a API só existe para guardar contas e resultados.

Consequência disso: uma prova terminada sem internet não pode se perder, então
`web/src/lib/outbox.ts` grava a tentativa em IndexedDB e a envia quando a
conexão volta. O `clienteId` torna o reenvio idempotente.

## Rodar

```bash
# 1. dados (uma vez, ou quando mudar a extração)
python tools/parse_exam.py        # PDFs -> JSON + PNG
python tools/build_db.py          # JSON -> data/questoes.sqlite
python tools/build_web.py         # JSON -> web/public/dados/ (payload do app)
python tools/gerar_icones.py      # ícones do PWA

# 2. backend
cd api && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
cp .env.example .env              # preencher com o Supabase
.venv/Scripts/python -m uvicorn app.main:app --reload

# 3. frontend
cd web && npm install
cp .env.example .env.local        # preencher com o Supabase
npm run dev
```

Testes: `cd api && .venv/Scripts/python -m pytest` (10 testes, validação de
token) e `cd web && npx vitest run` (17 testes, banco e gerador de simulado).

## Simulado

`web/src/simulado/gerar.ts` sorteia no mesmo perfil da prova real — idêntico em
2020, 2021 e 2022: **15 Linguagens, 15 Matemática, 15 Ciências Naturais, 5
Ciências Humanas**. O sorteio usa gerador com semente, então guardar um número
na tentativa basta para reconstruir exatamente a mesma prova depois.

Questão que depende de texto compartilhado é sorteada normalmente: o contexto é
exibido junto, então ela faz sentido sozinha sem arrastar as irmãs do texto.

## Estado atual

| | |
|---|---|
| Questões | 650 (50 por prova × 13 anos) |
| Alternativas | 2.750 (5 opções em 2008–2010, 4 a partir de 2011) |
| Contextos (texto/tira compartilhado) | 37 |
| Imagens vinculadas | 245 |
| Questões anuladas na origem | 1 (2009 q06, marcada `N` no gabarito) |
| Questões fora do banco | 4 (`revisar: true` — seguem nos JSON) |
| **Questões no SQLite** | **646** |
| Anos faltando | 2017, 2018 |

As 4 excluídas são de Matemática e têm alternativas desenhadas como vetor
(2008 q10, 2010 q46, 2016 q28, 2019 q28): o recorte da alternativa é limitado
pela altura do rótulo seguinte e corta figura alta pela base. Ficam registradas
nos JSON com `recorte_integral`; `python tools/build_db.py --incluir-revisar`
as inclui, se o recorte for corrigido depois.

## Estrutura

```
data/questoes/<ano>.json     fonte da verdade, versionada e editável à mão
data/imagens/<ano>/*.png     figuras recortadas das páginas
data/questoes.sqlite         banco gerado (não versionado)

tools/pdfio.py               extração de texto respeitando faixas e colunas
tools/sources.py             catálogo das provas: arquivo, dialeto, nº de alternativas
tools/parse_exam.py          PDF  -> JSON + PNG
tools/build_db.py            JSON -> SQLite
tools/build_web.py           JSON -> payload estático do PWA
tools/gerar_icones.py        ícones do PWA
tools/schema.sql             esquema do SQLite
tools/recon.py               diagnóstico dos PDFs (páginas, colunas, figuras)

api/app/auth.py              validação do JWT (HS256 ou JWKS)
api/app/main.py              rotas: /saude, /tentativas, /desempenho
api/schema.sql               tabelas de tentativa e resposta (Postgres)
api/tests/                   testes de autenticação

web/src/simulado/gerar.ts    sorteio balanceado, semente, correção
web/src/lib/outbox.ts        fila offline de envio (IndexedDB)
web/src/lib/banco.ts         carrega e cacheia o banco estático
web/src/telas/               Login, Início, Prova, Resultado
web/public/dados/            payload gerado (não versionado)
```

Os PDFs de origem **não estão no repositório**; ficam em
`OneDrive/Área de Trabalho/COOTEC/`, caminho definido em `tools/sources.py`.

## Como regerar

```bash
python tools/parse_exam.py          # todos os anos (regrava JSON e PNG)
python tools/parse_exam.py 2022     # um ano só
python tools/parse_exam.py --sem-imagens
python tools/build_db.py            # gera data/questoes.sqlite
```

Requisitos: Python 3.12 e `pymupdf`.

## Como a extração funciona

1. **Ordem de leitura.** As provas misturam páginas de 1 e 2 colunas. O texto é
   ordenado dividindo a página em faixas horizontais delimitadas por blocos que
   ocupam a largura inteira; dentro de cada faixa, lê-se a coluna esquerda toda
   e depois a direita. Sem isso a questão 01 se intercala com a 04.

2. **Dois dialetos.** 2008–2013 numeram como `01.`; 2014–2022 usam `QUESTÃO 01`.

3. **Figuras.** A maioria das ilustrações é **vetorial**, não imagem embutida
   (o PDF de 2016 tem 16.110 desenhos e só 11 imagens), então não há arquivo a
   extrair: a região da página é renderizada a 200 dpi. Uma faixa só conta como
   figura se contiver forma 2D ou imagem; traço fino isolado é descartado, pois o
   separador vertical de colunas e os fiozinhos do rótulo `QUESTÃO` são
   mobiliário de página. Traços finos em grupo de 3+ contam como grade de tabela.

4. **Alternativa que é fórmula.** Em várias questões de Matemática as opções são
   frações renderizadas como vetor, sem texto nenhum. Nesses casos a alternativa
   recebe `figura` com o recorte da própria opção. O recorte se estende para
   baixo o quanto o desenho exigir, senão a fração sai cortada ao meio.

5. **Conferência.** Onde a extração é duvidosa, a questão recebe `revisar: true`,
   o motivo em `motivo_revisao`, e um `recorte_integral`: a imagem da questão
   inteira, para comparar com o original sem abrir o PDF.

## Ressalvas conhecidas

- **Fórmula inline no enunciado.** Quando a frase tem uma fração no meio
  (`quando x + y = 2/5 e a – b = –5/8`), o valor é desenho e não texto: o
  enunciado extraído fica com a lacuna. Afeta 2008 q10, 2016 q28 e 2019 q28,
  que têm `recorte_integral` para leitura fiel e estão fora do banco.
- **Recorte de alternativa alta.** O recorte de uma alternativa-figura termina
  na altura do rótulo seguinte; figura que invade essa faixa sai cortada pela
  base (2010 q46, mapas com escala de longitude). Corrigir isso é o que falta
  para reaproveitar as 4 questões excluídas.
- **Texto dentro de tirinha.** Os balões de quadrinho são texto de verdade no
  PDF. Ficam em `texto_na_figura` (contextos) — servem de transcrição acessível,
  e a imagem carrega a versão visual.
- **Erros de digitação na origem.** Os PDFs de 2021 trazem `Língua Portugesa` e
  `Cências Humanas`; a detecção de matéria é tolerante a isso de propósito.
- **`materia` vs `area`.** As provas antigas separam História, Geografia e
  Ciências; as novas agrupam em Ciências Humanas/Naturais. `materia` preserva o
  impresso na prova; `area` é o eixo comum que permite sortear entre anos.

## Esquema do banco

`prova` → `contexto` → `questao` → `alternativa`, mais `imagem` (que aponta para
questão, contexto ou alternativa via `dono_tipo`/`dono_id`) e a view `v_questao`.
Busca textual em `questao_fts` (FTS5, sem acentuação).

Sorteio balanceado por área, descartando anulada e pendente de revisão:

```sql
SELECT id, ano, numero, materia, correta
  FROM questao
 WHERE area = 'Matemática' AND anulada = 0 AND revisar = 0
 ORDER BY RANDOM() LIMIT 10;
```
