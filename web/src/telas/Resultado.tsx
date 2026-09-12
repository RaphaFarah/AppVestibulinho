import { useState } from 'react'
import type { Banco, Letra, Simulado, TentativaLocal } from '../lib/tipos'
import { QuestaoView } from '../componentes/Questao'
import { corrigir } from '../simulado/gerar'

interface Props {
  banco: Banco
  simulado: Simulado
  tentativa: TentativaLocal
  onVoltar: () => void
}

export function Resultado({ banco, simulado, tentativa, onVoltar }: Props) {
  const [revisando, setRevisando] = useState(false)

  const marcadas = Object.fromEntries(
    tentativa.respostas.map((r) => [r.questaoId, r.marcada]),
  ) as Record<string, Letra | null>
  const r = corrigir(simulado.questoes, marcadas)
  const brancos = tentativa.respostas.filter((x) => !x.marcada).length
  const minutos = Math.round(tentativa.duracaoSegundos / 60)

  if (revisando) {
    return (
      <div className="revisao">
        <header className="barra">
          <span>Revisão</span>
          <button type="button" className="secundario" onClick={() => setRevisando(false)}>
            Voltar ao resultado
          </button>
        </header>
        {simulado.questoes.map((q, i) => (
          <QuestaoView
            key={q.id}
            questao={q}
            contexto={q.contextoId ? banco.contextos[q.contextoId] : undefined}
            posicao={i + 1}
            total={simulado.questoes.length}
            marcada={marcadas[q.id] ?? null}
            onMarcar={() => {}}
            revisando
          />
        ))}
      </div>
    )
  }

  return (
    <main className="cartao">
      <h1>
        {r.acertos} de {r.total}
      </h1>
      <p className="apoio">
        {((r.acertos / r.total) * 100).toFixed(0)}% de acerto · {minutos} min
        {brancos > 0 && ` · ${brancos} em branco`}
      </p>

      <table className="desempenho">
        <caption>Por área</caption>
        <tbody>
          {Object.entries(r.porArea).map(([area, d]) => (
            <tr key={area}>
              <th scope="row">{area}</th>
              <td>
                {d.acertos}/{d.total}
              </td>
              <td className="barra-dado">
                <span style={{ width: `${(d.acertos / d.total) * 100}%` }} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {!tentativa.sincronizada && (
        <p className="aviso">
          Resultado salvo neste aparelho. Será enviado à sua conta quando houver
          internet.
        </p>
      )}

      <div className="acoes">
        <button type="button" onClick={() => setRevisando(true)}>
          Revisar questões
        </button>
        <button type="button" className="secundario" onClick={onVoltar}>
          Início
        </button>
      </div>

      <p className="apoio">
        Semente {simulado.semente} — guarde para refazer exatamente esta prova.
      </p>
    </main>
  )
}
