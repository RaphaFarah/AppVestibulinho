import type { Contexto, Letra, Questao } from '../lib/tipos'
import { urlImagem } from '../lib/banco'

interface Props {
  questao: Questao
  contexto?: Contexto
  posicao: number
  total: number
  marcada: Letra | null
  onMarcar: (letra: Letra) => void
  /** na revisão, mostra o gabarito e destaca acerto e erro */
  revisando?: boolean
}

export function QuestaoView({
  questao, contexto, posicao, total, marcada, onMarcar, revisando = false,
}: Props) {
  return (
    <article className="questao">
      <header>
        <span className="contador">
          {posicao} de {total}
        </span>
        <span className="etiqueta">{questao.materia}</span>
        <span className="origem">
          {questao.ano} · questão {questao.numero}
        </span>
      </header>

      {contexto && (
        <section className="contexto">
          <p className="instrucao">{contexto.instrucao}</p>
          {contexto.texto && <p className="corrido">{contexto.texto}</p>}
          {contexto.figuras.map((f) => (
            <img key={f} src={urlImagem(f)} alt="" loading="lazy" />
          ))}
          {contexto.textoNaFigura && (
            // transcrição do que está escrito dentro da imagem: leitor de tela
            // e busca alcançam o conteúdo que só existe como desenho
            <p className="transcricao">
              <span>Transcrição da imagem:</span> {contexto.textoNaFigura}
            </p>
          )}
        </section>
      )}

      {questao.enunciado && <p className="enunciado">{questao.enunciado}</p>}

      {questao.figuras.map((f) => (
        <img key={f} src={urlImagem(f)} alt="" loading="lazy" />
      ))}

      <ul className="alternativas">
        {questao.alternativas.map((a) => {
          const escolhida = marcada === a.letra
          const classes = ['alternativa']
          if (escolhida) classes.push('escolhida')
          if (revisando && a.letra === questao.correta) classes.push('certa')
          if (revisando && escolhida && a.letra !== questao.correta) classes.push('errada')
          return (
            <li key={a.letra}>
              <button
                type="button"
                className={classes.join(' ')}
                aria-pressed={escolhida}
                disabled={revisando}
                onClick={() => onMarcar(a.letra)}
              >
                <span className="letra">{a.letra}</span>
                {a.texto ? (
                  <span className="corpo">{a.texto}</span>
                ) : a.figura ? (
                  // alternativa que é fórmula ou gráfico, não texto
                  <img className="corpo" src={urlImagem(a.figura)} alt={`Alternativa ${a.letra}`} />
                ) : null}
              </button>
            </li>
          )
        })}
      </ul>
    </article>
  )
}
