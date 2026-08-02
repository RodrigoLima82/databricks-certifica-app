import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Map, ChevronRight, ExternalLink, Pencil, ArrowRight, CheckCircle2, Circle } from 'lucide-react'
import { getRoutes, getProgress, markClass, unmarkClass, getCertInfo } from '@/services/api'
import { useAuth } from '@/context/AuthContext'
import { useT, useI18n } from '@/i18n'
import type { ClassItem } from '@/types'
import './Program.css'

export default function Routes() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const t = useT()
  const { lang } = useI18n()
  const qc = useQueryClient()
  const slug = user?.tenant_slug || ''
  const { data, isLoading } = useQuery({ queryKey: ['routes', slug, lang], queryFn: () => getRoutes(slug), enabled: !!slug })
  const { data: prog } = useQuery({ queryKey: ['progress'], queryFn: getProgress, enabled: !!slug })
  const done = new Set(prog?.completed ?? [])
  const toggle = useMutation({
    mutationFn: ({ id, on }: { id: string; on: boolean }) => on ? markClass(id) : unmarkClass(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['progress'] }); qc.invalidateQueries({ queryKey: ['leaderboard'] }) },
  })
  const [sel, setSel] = useState<number | null>(null)
  const selCert = sel != null ? (data?.routes?.[sel]?.certification_id || '') : ''
  const { data: certInfo } = useQuery({
    queryKey: ['certinfo', selCert, lang], queryFn: () => getCertInfo(selCert), enabled: !!selCert,
  })

  if (isLoading || !data) return <div className="spinner" />
  const canEdit = user?.is_admin || user?.is_superadmin
  const routes = data.routes || []
  const route = sel != null ? routes[sel] : null

  return (
    <div className="prog">
      <div className="au-title-row">
        <div>
          <h1 className="hist-title"><Map size={20} style={{ verticalAlign: -3 }} /> {t('routes.title')}</h1>
          <p className="muted hist-sub">{t('routes.pick')}</p>
        </div>
        {canEdit && (
          <button className="btn" onClick={() => navigate(`/rutas/editar${user?.is_superadmin && slug ? `?slug=${slug}` : ''}`)}>
            <Pencil size={15} /> {t('routes.editRoutes')}
          </button>
        )}
      </div>

      {routes.length === 0 ? (
        <p className="muted">{t('routes.empty')}</p>
      ) : route ? (
        <div>
          <button className="link-btn" onClick={() => setSel(null)}>{t('routes.back')}</button>
          <div className="card prog-hero" style={{ textAlign: 'left', padding: 24, marginTop: 8 }}>
            <h2>{route.name}</h2>
            <p className="muted">{route.description}</p>
            {route.certification_id && (
              <button className="btn btn-primary" style={{ marginTop: 12 }}
                onClick={() => navigate(`/cert/${route.certification_id}`)}>
                {t('routes.goTests')} <ArrowRight size={15} />
              </button>
            )}
          </div>

          {certInfo && (
            <div className="card" style={{ padding: 20, marginTop: 16 }}>
              <h3 style={{ marginBottom: 12 }}>{t('routes.certDetails')}</h3>
              <div className="prog-kpis" style={{ margin: 0 }}>
                <div className="card prog-kpi"><b>{certInfo.questions}</b><span>{t('routes.questions')}</span></div>
                <div className="card prog-kpi"><b>{certInfo.duration}</b><span>{t('routes.durationLabel')}</span></div>
                <div className="card prog-kpi"><b style={{ fontSize: 15 }}>{certInfo.language}</b><span>{t('routes.language')}</span></div>
                <div className="card prog-kpi"><b>{certInfo.validity}</b><span>{t('routes.validity')}</span></div>
              </div>
              <p className="muted" style={{ fontSize: 13, marginTop: 10 }}>{t('routes.experience')}: {certInfo.experience} · {certInfo.format}</p>

              <h4 style={{ margin: '16px 0 8px' }}>{t('routes.domains')}</h4>
              {certInfo.domains.map((d, i) => (
                <div key={i} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <span>{d.name}</span>{d.weight != null && <b>{d.weight}%</b>}
                  </div>
                  {d.weight != null && (
                    <div className="prog-bar" style={{ height: 7, margin: '3px 0 0' }}>
                      <div style={{ width: `${d.weight}%` }} />
                    </div>
                  )}
                </div>
              ))}
              {certInfo.exam_guide_url && (
                <a href={certInfo.exam_guide_url} target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 8 }}>
                  <ExternalLink size={14} /> {t('routes.examGuide')}
                </a>
              )}
            </div>
          )}

          {['fundamentos', 'associate', 'professional', ''].map(lv => {
            const group = route.classes.filter((c: ClassItem) => (c.level || '') === lv)
            if (group.length === 0) return null
            return (
              <div key={lv || 'otros'}>
                {lv && <h3 className="pe-h" style={{ fontSize: 14 }}>{t(`routes.lvl_${lv}`)}</h3>}
                {!lv && <h3 className="pe-h" style={{ fontSize: 14 }}>{t('routes.classes')}</h3>}
                <div className="prog-roadmap">
                  {group.map((c: ClassItem) => {
                    const isDone = done.has(c.id)
                    return (
                      <a key={c.id || c.title} className="card prog-step rt-class" target="_blank" rel="noreferrer"
                         href={c.url || '#'} style={isDone ? { borderColor: 'var(--brand-success)' } : undefined}>
                        <div className="prog-step-n" style={{ borderRadius: 8, background: isDone ? 'var(--brand-success)' : 'var(--brand-primary)' }}>
                          {isDone ? <CheckCircle2 size={16} /> : <ExternalLink size={15} />}
                        </div>
                        <div style={{ flex: 1 }}>
                          <h4 style={{ margin: 0 }}>{c.title}</h4>
                          <div className="muted" style={{ fontSize: 12, display: 'flex', gap: 10, marginTop: 4, alignItems: 'center' }}>
                            {c.free && <span className="badge badge-associate" style={{ background: 'var(--brand-success-bg)', color: 'var(--brand-success)' }}>{t('routes.free')}</span>}
                            {c.duration && <span>{c.duration}</span>}
                          </div>
                        </div>
                        {c.id && (
                          <button className="link-btn" style={{ color: isDone ? 'var(--brand-success)' : 'var(--brand-text-muted)' }}
                            title={t('routes.markDone')} disabled={toggle.isPending}
                            onClick={e => { e.preventDefault(); toggle.mutate({ id: c.id, on: !isDone }) }}>
                            {isDone ? <CheckCircle2 size={18} /> : <Circle size={18} />}
                          </button>
                        )}
                      </a>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="prog-grid">
          {routes.map((r, i) => (
            <button key={i} className="card prog-pillar" style={{ textAlign: 'left', cursor: 'pointer' }} onClick={() => setSel(i)}>
              <h4>{r.name} <ChevronRight size={15} style={{ verticalAlign: -2 }} /></h4>
              <p className="muted">{r.description}</p>
              <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
                {r.classes.filter(c => done.has(c.id)).length}/{r.classes.length} {t('routes.classes').toLowerCase()}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
