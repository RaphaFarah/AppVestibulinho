import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import type { Banco, Simulado, TentativaLocal } from './lib/tipos'
import { carregarBanco } from './lib/banco'
import { authConfigurada, supabase } from './lib/supabase'
import { observarConexao, sincronizar } from './lib/outbox'
import { Login } from './telas/Login'
import { Inicio } from './telas/Inicio'
import { Prova } from './telas/Prova'
import { Resultado } from './telas/Resultado'

type Tela =
  | { nome: 'inicio' }
  | { nome: 'prova'; simulado: Simulado; limite: number }
  | { nome: 'resultado'; simulado: Simulado; tentativa: TentativaLocal }

export default function App() {
  const [sessao, setSessao] = useState<Session | null>(null)
  const [carregandoSessao, setCarregandoSessao] = useState(true)
  const [banco, setBanco] = useState<Banco | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [tela, setTela] = useState<Tela>({ nome: 'inicio' })

  useEffect(() => {
    if (!supabase) {
      setCarregandoSessao(false)
      return
    }
    void supabase.auth.getSession().then(({ data }) => {
      setSessao(data.session)
      setCarregandoSessao(false)
    })
    const { data } = supabase.auth.onAuthStateChange((_evento, s) => {
      setSessao(s)
      // ao entrar, tenta despachar o que ficou pendente offline
      if (s) void sincronizar()
    })
    return () => data.subscription.unsubscribe()
  }, [])

  useEffect(() => {
    carregarBanco().then(setBanco).catch((e: Error) => setErro(e.message))
  }, [])

  useEffect(() => observarConexao(() => {}), [])

  if (!authConfigurada) {
    return (
      <main className="cartao estreito">
        <h1>Falta configurar</h1>
        <p>
          Crie <code>web/.env.local</code> com <code>VITE_SUPABASE_URL</code> e{' '}
          <code>VITE_SUPABASE_ANON_KEY</code>, copiando de{' '}
          <code>.env.example</code>, e recarregue.
        </p>
      </main>
    )
  }

  if (carregandoSessao) return <main className="cartao estreito">Carregando…</main>
  if (!sessao) return <Login />

  if (erro) {
    return (
      <main className="cartao estreito">
        <h1>Banco de questões indisponível</h1>
        <p className="erro">{erro}</p>
        <p className="apoio">
          Se for a primeira visita, conecte-se à internet uma vez para baixar as
          questões; depois o app funciona offline.
        </p>
      </main>
    )
  }
  if (!banco) return <main className="cartao estreito">Baixando questões…</main>

  if (tela.nome === 'prova') {
    return (
      <Prova
        banco={banco}
        simulado={tela.simulado}
        limiteSegundos={tela.limite}
        onTerminar={(tentativa) =>
          setTela({ nome: 'resultado', simulado: tela.simulado, tentativa })
        }
      />
    )
  }

  if (tela.nome === 'resultado') {
    return (
      <Resultado
        banco={banco}
        simulado={tela.simulado}
        tentativa={tela.tentativa}
        onVoltar={() => setTela({ nome: 'inicio' })}
      />
    )
  }

  return (
    <Inicio
      banco={banco}
      email={sessao.user.email ?? null}
      onComecar={(simulado, limite) => setTela({ nome: 'prova', simulado, limite })}
    />
  )
}
