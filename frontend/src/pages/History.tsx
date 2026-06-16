import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, XCircle, RefreshCw } from 'lucide-react'
import { getMyAttempts } from '@/services/api'
import './History.css'

export default function History() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({ queryKey: ['my-attempts'], queryFn: getMyAttempts })

  if (isLoading) return <div className="spinner" />

  const attempts = data?.attempts ?? []
  const passMark = data?.pass_mark ?? 70
  const fmt = (s?: string) => s ? new Date(s).toLocaleString('pt-BR') : '—'

  return (
    <div>
      <h1 className="hist-title">Meu histórico</h1>
      <p className="muted hist-sub">Todas as suas tentativas. Nota de corte: {passMark}%.</p>

      {attempts.length === 0 ? (
        <div className="card hist-empty">
          <p>Você ainda não fez nenhum simulado.</p>
          <button className="btn btn-primary" onClick={() => navigate('/')}>Começar agora</button>
        </div>
      ) : (
        <div className="card hist-table-wrap">
          <table className="hist-table">
            <thead>
              <tr>
                <th>Data</th><th>Certificação</th><th>Score</th>
                <th>Resultado</th><th>Repetidas</th><th>IA</th>
              </tr>
            </thead>
            <tbody>
              {attempts.map(a => (
                <tr key={a.session_id}>
                  <td>{fmt(a.created_at)}</td>
                  <td>{a.certification_name ?? a.certification_id}</td>
                  <td><b>{a.score_pct}%</b> <span className="muted">({a.correct}/{a.total})</span></td>
                  <td>
                    {a.passed
                      ? <span className="hist-badge ok"><CheckCircle2 size={14} /> Aprovado</span>
                      : <span className="hist-badge no"><XCircle size={14} /> Reprovado</span>}
                  </td>
                  <td>{a.repeated_questions > 0
                    ? <span className="hist-rep"><RefreshCw size={13} /> {a.repeated_questions}</span>
                    : <span className="muted">0</span>}</td>
                  <td>{a.ai_generated ? <span className="badge badge-ai">IA</span> : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
