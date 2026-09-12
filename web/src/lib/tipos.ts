export type Letra = 'A' | 'B' | 'C' | 'D' | 'E'

export interface Alternativa {
  letra: Letra
  /** nulo quando a alternativa é uma fórmula ou gráfico: usar `figura` */
  texto: string | null
  figura: string | null
}

export interface Contexto {
  id: string
  instrucao: string
  texto: string
  /** transcrição do que está dentro da figura (balões de tirinha, por exemplo) */
  textoNaFigura: string | null
  figuras: string[]
}

export interface Questao {
  id: string
  ano: number
  numero: number
  materia: string
  area: string
  contextoId: string | null
  enunciado: string
  alternativas: Alternativa[]
  correta: Letra
  figuras: string[]
}

export interface Banco {
  versao: string
  questoes: Questao[]
  contextos: Record<string, Contexto>
}

/** Quantas questões de cada área a prova deve ter. */
export type Perfil = Record<string, number>

export interface Simulado {
  semente: number
  perfil: Perfil
  questoes: Questao[]
  /** áreas que não tinham questões suficientes no banco */
  faltando: Record<string, number>
}

export interface RespostaDada {
  questaoId: string
  marcada: Letra | null
  correta: boolean
  segundos: number
}

export interface TentativaLocal {
  clienteId: string
  modo: 'simulado' | 'treino'
  semente: number
  totalQuestoes: number
  duracaoSegundos: number
  finalizadoEm: string
  respostas: RespostaDada[]
  /** já confirmada pelo servidor? */
  sincronizada: boolean
}
