import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, ExternalLink, Pencil, Trophy } from 'lucide-react'
import { getProgram, getLeaderboard, getProgramProgress } from '@/services/api'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { useT, useI18n } from '@/i18n'
import './Program.css'

export default function Program() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { theme } = useTheme()
  const t = useT()
  const { lang } = useI18n()
  const slug = user?.tenant_slug || ''
  const { data: p, isLoading } = useQuery({
    queryKey: ['program', slug, lang], queryFn: () => getProgram(slug), enabled: !!slug,
  })
  const { data: board } = useQuery({
    queryKey: ['leaderboard', slug], queryFn: getLeaderboard, enabled: !!p?.ranking_enabled,
  })
  const { data: prog } = useQuery({ queryKey: ['program-progress'], queryFn: getProgramProgress, enabled: !!slug })

  if (isLoading || !p) return <div className="spinner" />
  const canEdit = user?.is_admin || user?.is_superadmin

  return (
    <div className="prog">
      <section className="prog-hero card">
        {theme?.logo_url && <img src={theme.logo_url} alt="" className="prog-hero-logo" />}
        {p.title && <h1>{p.title}</h1>}
        {p.tagline && <p className="prog-tagline">{p.tagline}</p>}
        {p.intro && <p className="prog-intro">{p.intro}</p>}
        <div className="prog-hero-actions">
          <button className="btn btn-primary btn-lg" onClick={() => navigate('/simulacros')}>
            {t('program.startSimulacros')} <ArrowRight size={16} />
          </button>
          {canEdit && (
            <button className="btn" onClick={() => navigate(`/programa/editar${user?.is_superadmin && slug ? `?slug=${slug}` : ''}`)}>
              <Pencil size={15} /> {t('program.editProgram')}
            </button>
          )}
        </div>
      </section>

      {prog && (prog.classes_total > 0 || prog.certs_total > 0) && (
        <section className="card prog-progress">
          <div className="prog-progress-head">
            <h3>{t('program.yourProgress')}</h3>
            <b style={{ color: 'var(--brand-primary)', fontSize: 22 }}>{prog.percent}%</b>
          </div>
          <div className="prog-bar"><div style={{ width: `${prog.percent}%` }} /></div>
          <div className="prog-progress-meta muted">
            <span>{t('program.classesLabel')}: {prog.classes_done}/{prog.classes_total}</span>
            <span>{t('program.certsLabel')}: {prog.certs_passed}/{prog.certs_total}</span>
          </div>
        </section>
      )}

      {p.kpis?.length > 0 && (
        <section className="prog-kpis">
          {p.kpis.map((k, i) => (
            <div key={i} className="card prog-kpi"><b>{k.value}</b><span>{k.label}</span></div>
          ))}
        </section>
      )}

      {p.pillars?.length > 0 && (
        <section className="prog-section">
          <h2>{t('program.pillars')}</h2>
          <div className="prog-grid">
            {p.pillars.map((it, i) => (
              <div key={i} className="card prog-pillar"><h4>{it.title}</h4><p className="muted">{it.desc}</p></div>
            ))}
          </div>
        </section>
      )}

      {p.roadmap?.length > 0 && (
        <section className="prog-section">
          <h2>{t('program.roadmap')}</h2>
          <div className="prog-roadmap">
            {p.roadmap.map((it, i) => (
              <div key={i} className="card prog-step">
                <div className="prog-step-n">{i + 1}</div>
                <div>
                  <h4>{it.title}</h4>
                  <p className="muted">{it.desc}</p>
                  {it.link && (it.link.startsWith('/')
                    ? <button className="link-btn" onClick={() => navigate(it.link!)}>{t('program.startSimulacros')} →</button>
                    : <a href={it.link} target="_blank" rel="noreferrer">{it.link} <ExternalLink size={12} /></a>)}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {(p.exam_intro || (p.exam_steps && p.exam_steps.length > 0)) && (
        <section className="prog-section">
          <h2>{t('program.examTitle')}</h2>
          {p.exam_intro && (
            <div className="card" style={{ padding: 16, marginBottom: 12, borderLeft: '4px solid var(--brand-primary)' }}>
              <p className="muted" style={{ margin: 0 }}>{p.exam_intro}</p>
            </div>
          )}
          <div className="prog-roadmap">
            {p.exam_steps?.map((it, i) => (
              <div key={i} className="card prog-step">
                <div>
                  <h4 style={{ margin: 0 }}>{it.title}</h4>
                  <p className="muted" style={{ marginTop: 4 }}>{it.desc}</p>
                  {it.link && <a href={it.link} target="_blank" rel="noreferrer">{t('program.openLink')} <ExternalLink size={12} /></a>}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {p.resources?.length > 0 && (
        <section className="prog-section">
          <h2>{t('program.resources')}</h2>
          <ul className="prog-resources">
            {p.resources.map((r, i) => (
              <li key={i}><a href={r.url} target="_blank" rel="noreferrer"><ExternalLink size={14} /> {r.label}</a></li>
            ))}
          </ul>
        </section>
      )}

      {p.ranking_enabled && (
        <section className="prog-section">
          <h2><Trophy size={20} style={{ verticalAlign: -3 }} /> {t('program.ranking')}</h2>
          {p.ranking_intro && <p className="muted">{p.ranking_intro}</p>}
          <div className="prog-grid">
            {p.ranking_tiers?.map((it, i) => (
              <div key={i} className="card prog-pillar"><h4>{it.title}</h4><p className="muted">{it.desc}</p></div>
            ))}
          </div>
          <div className="card hist-table-wrap" style={{ marginTop: 16 }}>
            <h4 style={{ padding: '14px 16px 0' }}>{t('program.leaderboard')}</h4>
            {board && board.length > 0 ? (
              <table className="hist-table">
                <thead><tr><th>{t('program.rank')}</th><th>{t('admin.name')}</th><th>{t('admin.area')}</th><th>{t('program.points')}</th><th>{t('program.passed')}</th><th>{t('program.classesCol')}</th></tr></thead>
                <tbody>
                  {board.slice(0, 15).map(r => (
                    <tr key={r.email} style={r.email === user?.email ? { background: 'var(--brand-primary-pale)', fontWeight: 600 } : undefined}>
                      <td>{r.rank}</td>
                      <td>{r.name}{r.email === user?.email && ` · ${t('program.you')}`}</td>
                      <td className="muted">{r.area || '—'}</td>
                      <td><b>{r.points}</b></td>
                      <td>{r.passed}</td>
                      <td>{r.classes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="muted" style={{ padding: '0 16px 16px' }}>{t('program.noRanking')}</p>}
          </div>
        </section>
      )}
    </div>
  )
}
