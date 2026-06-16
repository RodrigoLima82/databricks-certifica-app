import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Users, ListChecks, Award, ChevronRight } from 'lucide-react'
import { getAdminOverview } from '@/services/api'
import './History.css'

export default function Admin() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({ queryKey: ['admin-overview'], queryFn: getAdminOverview })
  if (isLoading) return <div className="spinner" />
  if (!data) return <p className="muted">Sem dados.</p>

  const fmt = (s?: string) => s ? new Date(s).toLocaleString('pt-BR') : '—'
  const score = (v?: number) => v == null ? '—' : `${v}%`

  return (
    <div>
      <h1 className="hist-title">Painel administrativo</h1>
      <p className="muted hist-sub">Acompanhamento dos trainees. Nota de corte: {data.pass_mark}%.</p>

      <div className="adm-kpis">
        <div className="card adm-kpi"><Users size={20} color="#FF3621" /><div><b>{data.total_users}</b><span>Usuários</span></div></div>
        <div className="card adm-kpi"><ListChecks size={20} color="#FF3621" /><div><b>{data.total_attempts}</b><span>Tentativas</span></div></div>
        <div className="card adm-kpi"><Award size={20} color="#FF3621" /><div><b>{data.users.filter(u => u.passed_any).length}</b><span>Já aprovados</span></div></div>
      </div>

      <div className="card hist-table-wrap">
        <table className="hist-table">
          <thead>
            <tr><th>Nome</th><th>E-mail</th><th>Tentativas</th><th>Melhor</th><th>Última</th><th>Aprovado</th><th>Último acesso</th><th></th></tr>
          </thead>
          <tbody>
            {data.users.map(u => (
              <tr key={u.email}
                  className={u.attempts > 0 ? 'adm-row-click' : ''}
                  onClick={() => u.attempts > 0 && navigate(`/admin/user/${encodeURIComponent(u.email)}`)}
                  title={u.attempts > 0 ? 'Ver tentativas e respostas' : 'Sem tentativas'}>
                <td><b>{u.name}</b></td>
                <td className="muted">{u.email}</td>
                <td>{u.attempts}</td>
                <td>{score(u.best_score)}</td>
                <td>{score(u.last_score)}</td>
                <td>{u.passed_any
                  ? <span className="hist-badge ok">Sim</span>
                  : <span className="hist-badge no">Não</span>}</td>
                <td>{fmt(u.last_attempt_at)}</td>
                <td>{u.attempts > 0 && <ChevronRight size={16} color="#FF3621" />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
