import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import type { Banco } from '../lib/tipos'
import { PERFIL_PROVA, corrigir, embaralhar, gerarSimulado, prng } from './gerar'

// roda contra o banco real gerado por tools/build_web.py
const banco: Banco = JSON.parse(
  readFileSync(new URL('../../public/dados/banco.json', import.meta.url), 'utf8'),
)

describe('banco', () => {
  it('tem as 645 questões utilizáveis', () => {
    expect(banco.questoes.length).toBe(645)
  })

  it('toda questão tem gabarito e alternativas com conteúdo', () => {
    for (const q of banco.questoes) {
      expect(q.correta).toMatch(/^[A-E]$/)
      expect(q.alternativas.length).toBeGreaterThanOrEqual(4)
      expect(q.alternativas.some((a) => a.letra === q.correta)).toBe(true)
      for (const a of q.alternativas) expect(a.texto || a.figura).toBeTruthy()
    }
  })

  it('toda referência a contexto existe', () => {
    for (const q of banco.questoes) {
      if (q.contextoId) expect(banco.contextos[q.contextoId]).toBeDefined()
    }
  })

  // Verifica TODOS os contextos, não só os sorteados por uma semente: senão o
  // teste passa ou falha por sorte. O conteúdo pode estar no texto, na figura
  // ou na própria instrução, quando ela cita a frase analisada.
  it('nenhum contexto fica sem conteúdo para o aluno ler', () => {
    for (const c of Object.values(banco.contextos)) {
      const temConteudo =
        c.texto.trim().length > 0 || c.figuras.length > 0 || c.instrucao.length > 50
      expect(temConteudo, `contexto sem conteúdo: ${c.id}`).toBe(true)
    }
  })
})

describe('prng', () => {
  it('é determinístico para a mesma semente', () => {
    expect([prng(42)(), prng(42)(), prng(42)()]).toEqual(
      [prng(42)(), prng(42)(), prng(42)()],
    )
  })

  it('embaralhar preserva os itens', () => {
    const orig = [1, 2, 3, 4, 5, 6, 7, 8]
    const mex = embaralhar(orig, prng(7))
    expect([...mex].sort()).toEqual(orig)
    expect(orig).toEqual([1, 2, 3, 4, 5, 6, 7, 8]) // não muta a entrada
  })
})

describe('gerarSimulado', () => {
  it('respeita o perfil da prova real e soma 50', () => {
    const s = gerarSimulado(banco, { semente: 1 })
    expect(s.questoes.length).toBe(50)
    expect(s.faltando).toEqual({})
    for (const [area, n] of Object.entries(PERFIL_PROVA)) {
      expect(s.questoes.filter((q) => q.area === area).length).toBe(n)
    }
  })

  it('não repete questão', () => {
    const s = gerarSimulado(banco, { semente: 99 })
    expect(new Set(s.questoes.map((q) => q.id)).size).toBe(s.questoes.length)
  })

  it('mantém a ordem das áreas do caderno oficial', () => {
    const s = gerarSimulado(banco, { semente: 5 })
    const areas = s.questoes.map((q) => q.area)
    expect(areas).toEqual([...areas].sort(
      (a, b) => ['Linguagens', 'Matemática', 'Ciências Naturais', 'Ciências Humanas']
        .indexOf(a) -
        ['Linguagens', 'Matemática', 'Ciências Naturais', 'Ciências Humanas']
          .indexOf(b),
    ))
  })

  it('a mesma semente reconstrói exatamente a mesma prova', () => {
    const a = gerarSimulado(banco, { semente: 12345 })
    const b = gerarSimulado(banco, { semente: 12345 })
    expect(a.questoes.map((q) => q.id)).toEqual(b.questoes.map((q) => q.id))
  })

  it('sementes diferentes geram provas diferentes', () => {
    const a = gerarSimulado(banco, { semente: 1 }).questoes.map((q) => q.id)
    const b = gerarSimulado(banco, { semente: 2 }).questoes.map((q) => q.id)
    expect(a).not.toEqual(b)
  })

  it('filtra por ano', () => {
    const s = gerarSimulado(banco, { semente: 3, anos: [2022, 2021] })
    expect(new Set(s.questoes.map((q) => q.ano))).toEqual(new Set([2022, 2021]))
  })

  it('nunca sorteia questão excluída', () => {
    const primeiro = gerarSimulado(banco, { semente: 8 })
    const excluir = primeiro.questoes.map((q) => q.id)
    const segundo = gerarSimulado(banco, { semente: 8, excluir })
    expect(segundo.questoes.some((q) => excluir.includes(q.id))).toBe(false)
  })

  it('avisa quando o banco não tem questões suficientes', () => {
    const s = gerarSimulado(banco, {
      semente: 4, anos: [2022], perfil: { 'Ciências Humanas': 40 },
    })
    expect(s.faltando['Ciências Humanas']).toBeGreaterThan(0)
  })

  it('toda questão sorteada que depende de contexto o encontra no banco', () => {
    const s = gerarSimulado(banco, { semente: 77 })
    for (const q of s.questoes) {
      if (q.contextoId) expect(banco.contextos[q.contextoId]).toBeDefined()
    }
  })
})

describe('corrigir', () => {
  it('conta acertos e agrupa por área', () => {
    const s = gerarSimulado(banco, { semente: 2024 })
    const todasCertas = Object.fromEntries(s.questoes.map((q) => [q.id, q.correta]))
    const r = corrigir(s.questoes, todasCertas)
    expect(r.acertos).toBe(50)
    expect(r.porArea['Matemática']).toEqual({ acertos: 15, total: 15 })
  })

  it('em branco não conta como acerto', () => {
    const s = gerarSimulado(banco, { semente: 2025 })
    const nenhuma = Object.fromEntries(s.questoes.map((q) => [q.id, null]))
    expect(corrigir(s.questoes, nenhuma).acertos).toBe(0)
  })
})
