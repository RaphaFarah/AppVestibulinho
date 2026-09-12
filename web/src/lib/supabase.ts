import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY

/**
 * Fica nulo enquanto o .env.local não estiver preenchido, para o app subir e
 * mostrar o que falta em vez de quebrar numa tela branca.
 */
export const supabase: SupabaseClient | null =
  url && anon
    ? createClient(url, anon, {
        auth: {
          // sessão persistida e renovada sozinha: essencial num PWA, em que o
          // aluno fecha o app no meio da prova e volta depois
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
        },
      })
    : null

export const authConfigurada = supabase !== null

/** Token para mandar à API. Nulo se não houver sessão válida. */
export async function tokenAtual(): Promise<string | null> {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}
