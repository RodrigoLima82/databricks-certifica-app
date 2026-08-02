import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, XCircle, RefreshCw } from 'lucide-react'
import { getMyAttempts } from '@/services/api'
import { useT, useI18n } from '@/i18n'
import './History.css'

const LOCALE = { es: 'es-CL', pt: 'pt-BR', en: 'en-US' } as const

export default function History() {
  const navigate = useNavigate()
  const t = useT()
  const { lang } = useI18n()
  const { data, isLoading } = useQuery({ queryKey: ['my-attempts'], queryFn: getMyAttempts })

  if (isLoading) return <div className="spinner" />

  const attempts = data?.attempts ?? []
  const passMark = data?.pass_mark ?? 70
  const fmt = (s?: string) => s ? new Date(s).toLocaleString(LOCALE[lang]) : '—'

  return (
    <div>
      <h1 className="hist-title">{t('history.title')}</h1>
      <p className="muted hist-sub">{t('history.sub', { m: passMark })}</p>

      {attempts.length === 0 ? (
        <div className="card hist-empty">
          <p>{t('history.empty')}</p>
          <button className="btn btn-primary" onClick={() => navigate('/')}>{t('history.startNow')}</button>
        </div>
      ) : (
        <div className="card hist-table-wrap">
          <table className="hist-table">
            <thead>
              <tr>
                <th>{t('history.date')}</th><th>{t('history.certification')}</th><th>{t('history.score')}</th>
                <th>{t('history.result')}</th><th>{t('history.repeated')}</th><th>{t('history.ai')}</th>
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
                      ? <span className="hist-badge ok"><CheckCircle2 size={14} /> {t('history.approved')}</span>
                      : <span className="hist-badge no"><XCircle size={14} /> {t('history.reproved')}</span>}
                  </td>
                  <td>{a.repeated_questions > 0
                    ? <span className="hist-rep"><RefreshCw size={13} /> {a.repeated_questions}</span>
                    : <span className="muted">0</span>}</td>
                  <td>{a.ai_generated ? <span className="badge badge-ai">{t('history.ai')}</span> : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
