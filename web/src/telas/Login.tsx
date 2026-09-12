import { useState } from 'react'
import { supabase } from '../lib/supabase'

type Modo = 'entrar' | 'criar' | 'recuperar'

const ROTULO: Record<Modo, string> = {
  entrar: 'Entrar',
  criar: 'Criar conta',
  recuperar: 'Enviar link de recuperação',
}

/**
 * Senha nunca passa pela nossa API: o Supabase trata cadastro, confirmação de
 * e-mail e recuperação. Aqui só se coleta e-mail e senha e se mostra o retorno.
 */
export function Login() {
  const [modo, setModo] = useState<Modo>('entrar')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  async function enviar(e: React.FormEvent) {
    e.preventDefault()
    if (!supabase) return
    setOcupado(true)
    setErro(null)
    setAviso(null)
    try {
      if (modo === 'entrar') {
        const { error } = await supabase.auth.signInWithPassword({ email, password: senha })
        if (error) throw error
      } else if (modo === 'criar') {
        const { error } = await supabase.auth.signUp({ email, password: senha })
        if (error) throw error
        setAviso('Conta criada. Confira seu e-mail para confirmar o cadastro.')
      } else {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: window.location.origin,
        })
        if (error) throw error
        setAviso('Se este e-mail estiver cadastrado, o link de troca de senha chegou.')
      }
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'não foi possível concluir')
    } finally {
      setOcupado(false)
    }
  }

  return (
    <main className="cartao estreito">
      <h1>Vestibulinho</h1>
      <p className="apoio">
        Provas simuladas com questões reais do Vestibulinho ETEC, de 2008 a 2022.
      </p>

      <form onSubmit={enviar}>
        <label>
          E-mail
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </label>

        {modo !== 'recuperar' && (
          <label>
            Senha
            <input
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              autoComplete={modo === 'criar' ? 'new-password' : 'current-password'}
              minLength={8}
              required
            />
          </label>
        )}

        <button type="submit" disabled={ocupado}>
          {ocupado ? 'Aguarde…' : ROTULO[modo]}
        </button>
      </form>

      {erro && <p className="erro">{erro}</p>}
      {aviso && <p className="aviso">{aviso}</p>}

      <nav className="alternar">
        {modo !== 'entrar' && (
          <button type="button" className="texto" onClick={() => setModo('entrar')}>
            Já tenho conta
          </button>
        )}
        {modo !== 'criar' && (
          <button type="button" className="texto" onClick={() => setModo('criar')}>
            Criar conta
          </button>
        )}
        {modo !== 'recuperar' && (
          <button type="button" className="texto" onClick={() => setModo('recuperar')}>
            Esqueci a senha
          </button>
        )}
      </nav>
    </main>
  )
}
