import { openDB, type IDBPDatabase } from 'idb'
import type { TentativaLocal } from './tipos'
import { tokenAtual } from './supabase'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * Fila de envio das provas terminadas.
 *
 * O simulado roda offline, mas o histórico vive no servidor. Sem esta fila, uma
 * prova terminada sem rede seria simplesmente perdida. A prova é gravada aqui
 * primeiro e só sai da fila quando o servidor confirma; `clienteId` torna o
 * reenvio idempotente, então tentar de novo nunca duplica o registro.
 */
const BANCO = 'appvestibulinho'
const LOJA = 'tentativas'

let db: Promise<IDBPDatabase> | null = null

function abrir() {
  db ??= openDB(BANCO, 1, {
    upgrade(d) {
      const loja = d.createObjectStore(LOJA, { keyPath: 'clienteId' })
      loja.createIndex('sincronizada', 'sincronizada')
    },
  })
  return db
}

export async function guardar(t: TentativaLocal): Promise<void> {
  const d = await abrir()
  await d.put(LOJA, t)
}

export async function historico(): Promise<TentativaLocal[]> {
  const d = await abrir()
  const todas: TentativaLocal[] = await d.getAll(LOJA)
  return todas.sort((a, b) => b.finalizadoEm.localeCompare(a.finalizadoEm))
}

export async function pendentes(): Promise<TentativaLocal[]> {
  return (await historico()).filter((t) => !t.sincronizada)
}

/**
 * Tenta enviar tudo o que está pendente. Devolve quantas foram aceitas.
 * Silencioso quando não há rede ou sessão: será chamada de novo mais tarde.
 */
export async function sincronizar(): Promise<{ enviadas: number; pendentes: number }> {
  const fila = await pendentes()
  if (!fila.length) return { enviadas: 0, pendentes: 0 }

  const token = await tokenAtual()
  if (!token || !navigator.onLine) return { enviadas: 0, pendentes: fila.length }

  const d = await abrir()
  let enviadas = 0
  for (const t of fila) {
    try {
      const r = await fetch(`${API}/tentativas`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          cliente_id: t.clienteId,
          modo: t.modo,
          semente: t.semente,
          total_questoes: t.totalQuestoes,
          duracao_segundos: t.duracaoSegundos,
          finalizado_em: t.finalizadoEm,
          respostas: t.respostas.map((r) => ({
            questao_id: r.questaoId,
            marcada: r.marcada,
            correta: r.correta,
            segundos: r.segundos,
          })),
        }),
      })
      if (r.ok) {
        await d.put(LOJA, { ...t, sincronizada: true })
        enviadas++
      } else if (r.status === 401) {
        break // sessão expirou: para e tenta depois de renovar
      }
      // 4xx de validação fica na fila para inspeção, não trava as demais
    } catch {
      break // sem rede: o resto continua pendente
    }
  }
  return { enviadas, pendentes: (await pendentes()).length }
}

/** Dispara sincronização quando a conexão volta. */
export function observarConexao(aoSincronizar: () => void): () => void {
  const acao = () => void sincronizar().then(aoSincronizar)
  window.addEventListener('online', acao)
  return () => window.removeEventListener('online', acao)
}
