import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Plus, Trash2, Loader2 } from 'lucide-react'
import { getProgram, saveProgram } from '@/services/api'
import { useAuth } from '@/context/AuthContext'
import { useT } from '@/i18n'
import type { ProgramContent, ProgramItem, ProgramKpi, ProgramResource } from '@/types'
import './Program.css'

const EMPTY: ProgramContent = {
  title: '', tagline: '', intro: '', kpis: [], pillars: [], roadmap: [],
  exam_intro: '', exam_steps: [],
  resources: [], ranking_enabled: false, ranking_intro: '', ranking_tiers: [],
}

export default function ProgramEditor() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { user } = useAuth()
  const t = useT()
  const slug = params.get('slug') || user?.tenant_slug || ''
  const [p, setP] = useState<ProgramContent>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!slug) { setLoading(false); return }
    getProgram(slug).then(d => setP({ ...EMPTY, ...d })).finally(() => setLoading(false))
  }, [slug])

  const set = (k: keyof ProgramContent, v: any) => { setP(s => ({ ...s, [k]: v })); setSaved(false) }
  async function save() {
    setSaving(true)
    try { await saveProgram(slug, p); setSaved(true) } finally { setSaving(false) }
  }

  if (loading) return <div className="spinner" />

  // editor genérico de listas {title,desc,link}
  const ItemList = ({ k }: { k: 'pillars' | 'roadmap' | 'ranking_tiers' | 'exam_steps' }) => (
    <div className="pe-list">
      {(p[k] as ProgramItem[]).map((it, i) => (
        <div key={i} className="card pe-row">
          <input placeholder={t('program.itemTitle')} value={it.title}
            onChange={e => set(k, (p[k] as ProgramItem[]).map((x, j) => j === i ? { ...x, title: e.target.value } : x))} />
          <input placeholder={t('program.itemDesc')} value={it.desc}
            onChange={e => set(k, (p[k] as ProgramItem[]).map((x, j) => j === i ? { ...x, desc: e.target.value } : x))} />
          <input placeholder={t('program.itemLink')} value={it.link ?? ''}
            onChange={e => set(k, (p[k] as ProgramItem[]).map((x, j) => j === i ? { ...x, link: e.target.value } : x))} />
          <button className="link-btn" onClick={() => set(k, (p[k] as ProgramItem[]).filter((_, j) => j !== i))}><Trash2 size={15} /></button>
        </div>
      ))}
      <button className="link-btn" onClick={() => set(k, [...(p[k] as ProgramItem[]), { title: '', desc: '', link: '' }])}><Plus size={15} /> {t('program.add')}</button>
    </div>
  )

  return (
    <div className="prog" style={{ maxWidth: 760 }}>
      <button className="link-btn" onClick={() => navigate(-1)}>{t('program.back')}</button>
      <h1 className="hist-title" style={{ marginTop: 8 }}>{t('program.editorTitle')} · {slug}</h1>

      <div className="card pe-block">
        <label>{t('program.title')}<input value={p.title} onChange={e => set('title', e.target.value)} /></label>
        <label>{t('program.tagline')}<input value={p.tagline} onChange={e => set('tagline', e.target.value)} /></label>
        <label>{t('program.intro')}<textarea rows={3} value={p.intro} onChange={e => set('intro', e.target.value)} /></label>
      </div>

      <h3 className="pe-h">{t('program.kpis')}</h3>
      <div className="pe-list">
        {p.kpis.map((k, i) => (
          <div key={i} className="card pe-row">
            <input placeholder={t('program.kpiValue')} value={k.value} onChange={e => set('kpis', p.kpis.map((x, j) => j === i ? { ...x, value: e.target.value } : x))} />
            <input placeholder={t('program.kpiLabel')} value={k.label} onChange={e => set('kpis', p.kpis.map((x, j) => j === i ? { ...x, label: e.target.value } : x))} />
            <button className="link-btn" onClick={() => set('kpis', p.kpis.filter((_, j) => j !== i))}><Trash2 size={15} /></button>
          </div>
        ))}
        <button className="link-btn" onClick={() => set('kpis', [...p.kpis, { label: '', value: '' } as ProgramKpi])}><Plus size={15} /> {t('program.add')}</button>
      </div>

      <h3 className="pe-h">{t('program.pillars')}</h3><ItemList k="pillars" />
      <h3 className="pe-h">{t('program.roadmap')}</h3><ItemList k="roadmap" />

      <h3 className="pe-h">{t('program.examTitle')}</h3>
      <div className="card pe-block"><label>{t('program.examIntroLabel')}<textarea rows={3} value={p.exam_intro} onChange={e => set('exam_intro', e.target.value)} /></label></div>
      <ItemList k="exam_steps" />

      <h3 className="pe-h">{t('program.resources')}</h3>
      <div className="pe-list">
        {p.resources.map((r, i) => (
          <div key={i} className="card pe-row">
            <input placeholder={t('program.resLabel')} value={r.label} onChange={e => set('resources', p.resources.map((x, j) => j === i ? { ...x, label: e.target.value } : x))} />
            <input placeholder={t('program.resUrl')} value={r.url} onChange={e => set('resources', p.resources.map((x, j) => j === i ? { ...x, url: e.target.value } : x))} />
            <button className="link-btn" onClick={() => set('resources', p.resources.filter((_, j) => j !== i))}><Trash2 size={15} /></button>
          </div>
        ))}
        <button className="link-btn" onClick={() => set('resources', [...p.resources, { label: '', url: '' } as ProgramResource])}><Plus size={15} /> {t('program.add')}</button>
      </div>

      <h3 className="pe-h">
        <label style={{ display: 'inline-flex', gap: 8, alignItems: 'center', fontSize: 'inherit' }}>
          <input type="checkbox" checked={p.ranking_enabled} onChange={e => set('ranking_enabled', e.target.checked)} style={{ width: 'auto' }} />
          {t('program.ranking')}
        </label>
      </h3>
      {p.ranking_enabled && (
        <div className="pe-list">
          <div className="card pe-block"><label>{t('program.rankingIntro')}<textarea rows={2} value={p.ranking_intro} onChange={e => set('ranking_intro', e.target.value)} /></label></div>
          <ItemList k="ranking_tiers" />
        </div>
      )}

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', margin: '24px 0 40px' }}>
        <button className="btn btn-primary btn-lg" disabled={saving} onClick={save}>
          {saving ? <Loader2 size={16} className="spinning" /> : t('program.save')}
        </button>
        {saved && <span style={{ color: 'var(--brand-success)' }}>{t('program.saved')}</span>}
      </div>
    </div>
  )
}
