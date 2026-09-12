import type { Banco } from './tipos'

const CAMINHO = `${import.meta.env.BASE_URL}dados/banco.json`

let cache: Promise<Banco> | null = null

/**
 * Carrega o banco de questões uma única vez por sessão.
 *
 * O arquivo é estático e o service worker o mantém em cache, então depois da
 * primeira visita isto resolve offline -- é o que permite fazer prova sem rede.
 */
export function carregarBanco(): Promise<Banco> {
  cache ??= fetch(CAMINHO)
    .then((r) => {
      if (!r.ok) throw new Error(`banco de questões indisponível (${r.status})`)
      return r.json() as Promise<Banco>
    })
    .catch((e) => {
      cache = null // permite tentar de novo depois de uma falha de rede
      throw e
    })
  return cache
}

/** Caminho da imagem dentro do payload: 'imagens/2022/x.png' -> URL servível. */
export function urlImagem(relativo: string): string {
  return `${import.meta.env.BASE_URL}dados/${relativo}`
}

export function anosDisponiveis(banco: Banco): number[] {
  return [...new Set(banco.questoes.map((q) => q.ano))].sort((a, b) => b - a)
}
