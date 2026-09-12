import { useEffect, useState } from 'react'
import type { Banco, Simulado, TentativaLocal } from '../lib/tipos'
import { anosDisponiveis } from '../lib/banco'
import { gerarSimulado } from '../simulado/gerar'
import { historico, pendentes, sincronizar } from '../lib/outbox'
import { supabase } from '../lib/supabase'
import { DURACAO_PADRAO } from './Prova'

interface Props {
  banco: Banco
  email: string | null
  onComecar: (s: Simulado, limiteSegundos: number) => void
}

export function Inicio({ banco, email, onComecar }: Props) {
  const anos = anosDisponiveis(banco)
  const [selecionados, setSelecionados] = useState<number[]>([])
  const [cronometrar, setCronometrar] = useState(true)
  const [evitarRepetidas, setEvitarRepetidas] = useState(true)
  const [feitas, setFeitas] = useState<TentativaLocal[]>([])
  const [naFila, setNaFila] = useState(0)

  useEffect(() => {
    void historico().then(setFeitas)
    void pendentes().then((p) => setNaFila(p.length))
  }, [])

  async function comecar() {
    // questões já respondidas saem do sorteio, para o treino não repetir
    const jaVistas = evitarRepetidas
      ? (await historico()).flatMap((t) => t.respostas.map((r) => r.questaoId))
      : []
    const s = gerarSimulado(banco, { anos: selecionados, excluir: jaVistas })
    onComecar(s, cronometrar ? DURACAO_PADRAO : Number.MAX_SAFE_INTEGER)
  }

  function alternarAno(ano: number) {
    setSelecionados((atual) =>
      atual.includes(ano) ? atual.filter((a) => a !== ano) : [...atual, ano],
    )
  }

  return (
    <main className="cartao">
      <header className="topo">
        <h1>Vestibulinho</h1>
        {email && (
          <span className="apoio">
            {email}{' '}
            <button type="button" className="texto" onClick={() => supabase?.auth.signOut()}>
              sair
            </button>
          </span>
        )}
      </header>

      <p className="apoio">
        {banco.questoes.length} questões reais de {anos.length} provas ({anos.at(-1)}–
        {anos[0]}). Banco atualizado em {banco.versao}.
      </p>

      <section>
        <h2>Anos</h2>
        <p className="apoio">Nenhum marcado = sorteia de todos.</p>
        <div className="chips">
          {anos.map((ano) => (
            <button
              type="button"
              key={ano}
              className={selecionados.includes(ano) ? 'chip ativo' : 'chip'}
              aria-pressed={selecionados.includes(ano)}
              onClick={() => alternarAno(ano)}
            >
              {ano}
            </button>
          ))}
        </div>
      </section>

      <section>
        <label className="linha">
          <input
            type="checkbox"
            checked={cronometrar}
            onChange={(e) => setCronometrar(e.target.checked)}
          />
          Cronometrar em 4h30, como na prova real
        </label>
        <label className="linha">
          <input
            type="checkbox"
            checked={evitarRepetidas}
            onChange={(e) => setEvitarRepetidas(e.target.checked)}
          />
          Evitar questões que eu já respondi
        </label>
      </section>

      <button type="button" className="principal" onClick={() => void comecar()}>
        Começar simulado de 50 questões
      </button>

      {naFila > 0 && (
        <p className="aviso">
          {naFila} {naFila === 1 ? 'prova' : 'provas'} aguardando envio.{' '}
          <button
            type="button"
            className="texto"
            onClick={() => void sincronizar().then((r) => setNaFila(r.pendentes))}
          >
            tentar agora
          </button>
        </p>
      )}

      {feitas.length > 0 && (
        <section>
          <h2>Suas provas</h2>
          <ul className="historico">
            {feitas.slice(0, 10).map((t) => {
              const acertos = t.respostas.filter((r) => r.correta).length
              return (
                <li key={t.clienteId}>
                  <span>{new Date(t.finalizadoEm).toLocaleDateString('pt-BR')}</span>
                  <strong>
                    {acertos}/{t.totalQuestoes}
                  </strong>
                  <span className="apoio">
                    {Math.round(t.duracaoSegundos / 60)} min
                    {!t.sincronizada && ' · não enviada'}
                  </span>
                </li>
              )
            })}
          </ul>
        </section>
      )}
    </main>
  )
}
