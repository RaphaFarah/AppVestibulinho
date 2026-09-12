import { useEffect, useMemo, useRef, useState } from 'react'
import type { Banco, Letra, Simulado, TentativaLocal } from '../lib/tipos'
import { QuestaoView } from '../componentes/Questao'
import { guardar, sincronizar } from '../lib/outbox'

/** Duração da prova real de Conhecimentos Gerais: 4h30. */
export const DURACAO_PADRAO = 4 * 3600 + 30 * 60

function relogio(segundos: number) {
  const s = Math.max(0, segundos)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${h}:${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

interface Props {
  banco: Banco
  simulado: Simulado
  limiteSegundos: number
  onTerminar: (t: TentativaLocal) => void
}

export function Prova({ banco, simulado, limiteSegundos, onTerminar }: Props) {
  const [indice, setIndice] = useState(0)
  const [marcadas, setMarcadas] = useState<Record<string, Letra | null>>({})
  const [restante, setRestante] = useState(limiteSegundos)
  const [confirmando, setConfirmando] = useState(false)

  const inicio = useRef(Date.now())
  const entrouNaQuestao = useRef(Date.now())
  const segundosPorQuestao = useRef<Record<string, number>>({})

  const questao = simulado.questoes[indice]
  const contexto = questao.contextoId ? banco.contextos[questao.contextoId] : undefined
  const respondidas = Object.values(marcadas).filter(Boolean).length

  // cronômetro: recalcula pelo relógio, não por contagem de ticks, senão o
  // tempo congela quando o navegador suspende a aba em segundo plano
  useEffect(() => {
    const t = setInterval(() => {
      const gasto = Math.floor((Date.now() - inicio.current) / 1000)
      setRestante(limiteSegundos - gasto)
    }, 1000)
    return () => clearInterval(t)
  }, [limiteSegundos])

  const terminar = useMemo(
    () => async (automatico = false) => {
      registrarTempo()
      const respostas = simulado.questoes.map((q) => ({
        questaoId: q.id,
        marcada: marcadas[q.id] ?? null,
        correta: marcadas[q.id] === q.correta,
        segundos: Math.round(segundosPorQuestao.current[q.id] ?? 0),
      }))
      const tentativa: TentativaLocal = {
        clienteId: crypto.randomUUID(),
        modo: 'simulado',
        semente: simulado.semente,
        totalQuestoes: simulado.questoes.length,
        duracaoSegundos: Math.floor((Date.now() - inicio.current) / 1000),
        finalizadoEm: new Date().toISOString(),
        respostas,
        sincronizada: false,
      }
      // grava antes de tentar a rede: prova terminada offline não se perde
      await guardar(tentativa)
      void sincronizar()
      onTerminar(tentativa)
      if (automatico) console.info('tempo esgotado: prova encerrada')
    },
    [marcadas, onTerminar, simulado],
  )

  useEffect(() => {
    if (restante <= 0) void terminar(true)
  }, [restante, terminar])

  function registrarTempo() {
    const id = simulado.questoes[indice].id
    const gasto = (Date.now() - entrouNaQuestao.current) / 1000
    segundosPorQuestao.current[id] = (segundosPorQuestao.current[id] ?? 0) + gasto
    entrouNaQuestao.current = Date.now()
  }

  function irPara(novo: number) {
    if (novo < 0 || novo >= simulado.questoes.length) return
    registrarTempo()
    setIndice(novo)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="prova">
      <header className="barra">
        <span className={restante < 300 ? 'relogio urgente' : 'relogio'}>
          {relogio(restante)}
        </span>
        <span className="progresso">
          {respondidas}/{simulado.questoes.length} respondidas
        </span>
        <button type="button" className="secundario" onClick={() => setConfirmando(true)}>
          Entregar
        </button>
      </header>

      <QuestaoView
        questao={questao}
        contexto={contexto}
        posicao={indice + 1}
        total={simulado.questoes.length}
        marcada={marcadas[questao.id] ?? null}
        onMarcar={(letra) =>
          setMarcadas((m) => ({
            ...m,
            // clicar de novo na mesma alternativa desmarca
            [questao.id]: m[questao.id] === letra ? null : letra,
          }))
        }
      />

      <nav className="navegacao">
        <button type="button" onClick={() => irPara(indice - 1)} disabled={indice === 0}>
          Anterior
        </button>
        <button
          type="button"
          onClick={() => irPara(indice + 1)}
          disabled={indice === simulado.questoes.length - 1}
        >
          Próxima
        </button>
      </nav>

      <ol className="mapa" aria-label="Mapa de questões">
        {simulado.questoes.map((q, i) => (
          <li key={q.id}>
            <button
              type="button"
              className={[
                'bolinha',
                marcadas[q.id] ? 'feita' : '',
                i === indice ? 'atual' : '',
              ].join(' ')}
              onClick={() => irPara(i)}
              aria-label={`Questão ${i + 1}${marcadas[q.id] ? ', respondida' : ''}`}
            >
              {i + 1}
            </button>
          </li>
        ))}
      </ol>

      {confirmando && (
        <div className="modal" role="dialog" aria-modal="true">
          <div className="cartao estreito">
            <h2>Entregar a prova?</h2>
            <p>
              Você respondeu {respondidas} de {simulado.questoes.length} questões.
              {respondidas < simulado.questoes.length &&
                ' As que ficarem em branco contam como erro.'}
            </p>
            <div className="acoes">
              <button type="button" onClick={() => void terminar()}>
                Entregar
              </button>
              <button type="button" className="secundario" onClick={() => setConfirmando(false)}>
                Continuar prova
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
