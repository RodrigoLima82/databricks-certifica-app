import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Activity, LogIn, Users, Download, Loader2 } from 'lucide-react'
import { getAdminActivity, getAdminActivityCsv } from '@/services/api'
import { downloadBlob } from '@/lib/export'
import { useT, useI18n } from '@/i18n'
import type { ActivityEvent } from '@/types'
import './History.css'

const LOCALE = { es: 'es-CL', pt: 'pt-BR', en: 'en-US' } as const

const ACTION_OPTIONS = [
  'login', 'register', 'password_change', 'test_submit', 'question_generate', 'class_complete',
]

type TFn = (key: string, vars?: Record<string, string | number>) => string

function actionLabel(t: TFn, action: string): string {
  const label = t(`activity.actions.${action}`)
  // se não houver tradução, o lookup devolve a própria key — mostra o raw nesse caso
  return label && !label.startsWith('activity.actions.') ? label : action
}

function summarizeDetail(action: string, detail: Record<string, any>): string {
  if (!detail || Object.keys(detail).length === 0) return '—'
  switch (action) {
    case 'test_submit':
      return `${detail.certification_id ?? ''} · ${detail.score_pct ?? '?'}% (${detail.correct ?? '?'}/${detail.total ?? '?'})${detail.passed ? ' ✓' : ''}`
    case 'question_generate':
      return `${detail.certification_id ?? ''} · ${detail.count ?? 0} q`
    case 'class_complete':
      return String(detail.class_id ?? '—')
    default:
      return Object.entries(detail)
        .map(([k, v]) => `${k}=${v !== null && typeof v === 'object' ? JSON.stringify(v) : v}`)
        .join(' · ')
  }
}

export default function AdminActivity() {
  const navigate = useNavigate()
  const t = useT()
  const { lang } = useI18n()
  const [action, setAction] = useState<string>('')
  const [email, setEmail] = useState<string>('')
  const [downloading, setDownloading] = useState(false)
  const [exportErr, setExportErr] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-activity', action, email],
    queryFn: () => getAdminActivity({
      action: action || undefined,
      email: email.trim() || undefined,
      limit: 500,
    }),
  })

  const fmt = (s?: string | null) => s ? new Date(s).toLocaleString(LOCALE[lang]) : '—'

  async function exportCsv() {
    setDownloading(true)
    setExportErr(null)
    try {
      const blob = await getAdminActivityCsv({ action: action || undefined, email: email.trim() || undefined })
      downloadBlob(blob, 'activity_log.csv')
    } catch (e: any) {
      setExportErr(e?.response?.data?.detail ?? t('activity.exportError'))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div>
      <div className="au-title-row">
        <div>
          <button className="btn" style={{ marginBottom: 10 }} onClick={() => navigate('/admin')}>
            {t('activity.back')}
          </button>
          <h1 className="hist-title">{t('activity.title')}</h1>
          <p className="muted hist-sub">{t('activity.sub')}</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <button className="btn btn-primary" disabled={downloading} onClick={exportCsv}>
            {downloading ? <Loader2 size={16} className="spinning" /> : <Download size={16} />} {t('activity.export')}
          </button>
          {exportErr && <div className="login-error" style={{ marginTop: 8 }}>{exportErr}</div>}
        </div>
      </div>

      <div className="adm-kpis">
        <div className="card adm-kpi"><Activity size={20} color="var(--brand-primary)" /><div><b>{data?.total_events ?? 0}</b><span>{t('activity.totalEvents')}</span></div></div>
        <div className="card adm-kpi"><LogIn size={20} color="var(--brand-primary)" /><div><b>{data?.logins_7d ?? 0}</b><span>{t('activity.logins7d')}</span></div></div>
        <div className="card adm-kpi"><Users size={20} color="var(--brand-primary)" /><div><b>{data?.active_users_7d ?? 0}</b><span>{t('activity.activeUsers7d')}</span></div></div>
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
        <select value={action} onChange={e => setAction(e.target.value)} style={{ maxWidth: 220 }}
                aria-label={t('activity.filterAction')}>
          <option value="">{t('activity.filterAction')}</option>
          {ACTION_OPTIONS.map(a => <option key={a} value={a}>{actionLabel(t, a)}</option>)}
        </select>
        <input value={email} onChange={e => setEmail(e.target.value)}
               aria-label={t('activity.filterUser')}
               placeholder={t('activity.filterUser')} style={{ maxWidth: 260 }} />
      </div>

      {isLoading ? <div className="spinner" /> : !data || data.events.length === 0 ? (
        <p className="muted">{t('activity.noEvents')}</p>
      ) : (
        <div className="card hist-table-wrap">
          <table className="hist-table">
            <thead>
              <tr>
                <th>{t('activity.when')}</th><th>{t('activity.user')}</th>
                <th>{t('activity.action')}</th><th>{t('activity.detail')}</th><th>{t('activity.ip')}</th>
              </tr>
            </thead>
            <tbody>
              {data.events.map((e: ActivityEvent) => (
                <tr key={e.id}>
                  <td>{fmt(e.created_at)}</td>
                  <td>
                    <b>{e.user_name || e.user_email}</b>
                    <div className="muted" style={{ fontSize: 12 }}>{e.user_email}</div>
                  </td>
                  <td><span className="badge badge-associate">{actionLabel(t, e.action)}</span></td>
                  <td className="muted" style={{ fontSize: 13 }}>{summarizeDetail(e.action, e.detail)}</td>
                  <td className="muted" style={{ fontSize: 12 }}>{e.ip || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
