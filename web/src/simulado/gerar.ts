import type { Banco, Perfil, Questao, Simulado } from '../lib/tipos'

/**
 * Distribuição real da prova de Conhecimentos Gerais: idêntica em 2020, 2021 e
 * 2022 (15 / 15 / 15 / 5). O simulado imita isso para treinar no mesmo ritmo
 * da prova verdadeira.
 */
export const PERFIL_PROVA: Perfil = {
  Linguagens: 15,
  'Matemática': 15,
  'Ciências Naturais': 15,
  'Ciências Humanas': 5,
}

/** Ordem em que as áreas aparecem no caderno oficial. */
export const ORDEM_AREAS = [
  'Linguagens',
  'Matemática',
  'Ciências Naturais',
  'Ciências Humanas',
]

/**
 * Gerador pseudoaleatório com semente (mulberry32). Usar semente em vez de
 * Math.random permite guardar só um número na tentativa e reconstruir a mesma
 * prova depois -- para revisar, comparar ou refazer.
 */
export function prng(semente: number): () => number {
  let a = semente >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** Fisher-Yates sobre uma cópia, usando o gerador com semente. */
export function embaralhar<T>(itens: readonly T[], rnd: () => number): T[] {
  const r = [...itens]
  for (let i = r.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1))
    ;[r[i], r[j]] = [r[j], r[i]]
  }
  return r
}

export interface Opcoes {
  perfil?: Perfil
  semente?: number
  /** restringe a certos anos; vazio ou ausente = todos */
  anos?: number[]
  /** ids a evitar, por exemplo questões já respondidas recentemente */
  excluir?: Iterable<string>
}

/**
 * Sorteia uma prova balanceada por área.
 *
 * Questões que dependem de texto compartilhado são mantidas: o contexto é
 * exibido junto com a questão, então ela faz sentido sozinha e não é preciso
 * arrastar as irmãs do mesmo texto para dentro da prova.
 */
export function gerarSimulado(banco: Banco, opcoes: Opcoes = {}): Simulado {
  const perfil = opcoes.perfil ?? PERFIL_PROVA
  const semente = opcoes.semente ?? Math.floor(Math.random() * 2 ** 31)
  const rnd = prng(semente)
  const anos = opcoes.anos && opcoes.anos.length ? new Set(opcoes.anos) : null
  const excluir = new Set(opcoes.excluir ?? [])

  const disponiveis = banco.questoes.filter(
    (q) => (!anos || anos.has(q.ano)) && !excluir.has(q.id),
  )

  const porArea = new Map<string, Questao[]>()
  for (const q of disponiveis) {
    const lista = porArea.get(q.area)
    if (lista) lista.push(q)
    else porArea.set(q.area, [q])
  }

  const escolhidas: Questao[] = []
  const faltando: Record<string, number> = {}

  const areas = Object.keys(perfil).sort(
    (a, b) => ORDEM_AREAS.indexOf(a) - ORDEM_AREAS.indexOf(b),
  )
  for (const area of areas) {
    const querido = perfil[area]
    const pool = porArea.get(area) ?? []
    const sorteadas = embaralhar(pool, rnd).slice(0, querido)
    if (sorteadas.length < querido) faltando[area] = querido - sorteadas.length
    escolhidas.push(...sorteadas)
  }

  return { semente, perfil, questoes: escolhidas, faltando }
}

/** Corrige uma prova comparando o que foi marcado com o gabarito. */
export function corrigir(
  questoes: readonly Questao[],
  marcadas: Readonly<Record<string, string | null>>,
) {
  let acertos = 0
  const porArea: Record<string, { acertos: number; total: number }> = {}
  for (const q of questoes) {
    const acertou = marcadas[q.id] === q.correta
    if (acertou) acertos++
    const a = (porArea[q.area] ??= { acertos: 0, total: 0 })
    a.total++
    if (acertou) a.acertos++
  }
  return { acertos, total: questoes.length, porArea }
}
