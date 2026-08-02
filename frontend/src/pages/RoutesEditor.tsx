import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Plus, Trash2, Loader2 } from 'lucide-react'
import { getRoutes, saveRoutes } from '@/services/api'
import { useAuth } from '@/context/AuthContext'
import { useT } from '@/i18n'
import type { RoutesContent, RouteItem, ClassItem } from '@/types'
import './Program.css'

const LEVELS = ['fundamentos', 'associate', 'professional']
const NEW_CLASS: ClassItem = { id: '', title: '', desc: '', type: 'elearning', level: 'fundamentos', duration: '', free: true, url: '' }
const NEW_ROUTE: RouteItem = { name: '', description: '', certification_id: '', classes: [] }

export default function RoutesEditor() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { user } = useAuth()
  const t = useT()
  const slug = params.get('slug') || user?.tenant_slug || ''
  const [data, setData] = useState<RoutesContent>({ routes: [] })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!slug) { setLoading(false); return }
    getRoutes(slug).then(d => setData({ routes: d.routes || [] })).finally(() => setLoading(false))
  }, [slug])

  const upd = (routes: RouteItem[]) => { setData({ routes }); setSaved(false) }
  const setRoute = (i: number, r: Partial<RouteItem>) => upd(data.routes.map((x, j) => j === i ? { ...x, ...r } : x))
  const setClass = (ri: number, ci: number, c: Partial<ClassItem>) =>
    setRoute(ri, { classes: data.routes[ri].classes.map((x, j) => j === ci ? { ...x, ...c } : x) })

  async function save() {
    setSaving(true)
    try { await saveRoutes(slug, data); setSaved(true) } finally { setSaving(false) }
  }
  if (loading) return <div className="spinner" />

  return (
    <div className="prog" style={{ maxWidth: 820 }}>
      <button className="link-btn" onClick={() => navigate(-1)}>{t('routes.back')}</button>
      <h1 className="hist-title" style={{ marginTop: 8 }}>{t('routes.editorTitle')} · {slug}</h1>

      {data.routes.map((r, ri) => (
        <div key={ri} className="card pe-block" style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input style={{ flex: 1 }} placeholder={t('routes.routeName')} value={r.name} onChange={e => setRoute(ri, { name: e.target.value })} />
            <button className="link-btn" onClick={() => upd(data.routes.filter((_, j) => j !== ri))}><Trash2 size={16} /></button>
          </div>
          <input placeholder={t('routes.routeDesc')} value={r.description} onChange={e => setRoute(ri, { description: e.target.value })} />
          <input placeholder={t('routes.cert')} value={r.certification_id ?? ''} onChange={e => setRoute(ri, { certification_id: e.target.value })} />

          <h4 style={{ margin: '8px 0 2px' }}>{t('routes.classes')}</h4>
          {r.classes.map((c, ci) => (
            <div key={ci} className="card pe-row" style={{ gridTemplateColumns: '2fr 1fr 1fr auto' }}>
              <input placeholder={t('routes.classTitle')} value={c.title} onChange={e => setClass(ri, ci, { title: e.target.value })} />
              <select value={c.level || 'fundamentos'} onChange={e => setClass(ri, ci, { level: e.target.value })}
                style={{ padding: '9px', borderRadius: 'var(--radius)', border: '1px solid var(--brand-border)' }}>
                {LEVELS.map(lv => <option key={lv} value={lv}>{t(`routes.lvl_${lv}`)}</option>)}
              </select>
              <input placeholder={t('routes.classDuration')} value={c.duration} onChange={e => setClass(ri, ci, { duration: e.target.value })} />
              <button className="link-btn" onClick={() => setRoute(ri, { classes: r.classes.filter((_, j) => j !== ci) })}><Trash2 size={15} /></button>
              <input style={{ gridColumn: '1 / -1' }} placeholder={t('routes.classUrl')} value={c.url ?? ''} onChange={e => setClass(ri, ci, { url: e.target.value })} />
            </div>
          ))}
          <button className="link-btn" onClick={() => setRoute(ri, { classes: [...r.classes, { ...NEW_CLASS, id: crypto.randomUUID() }] })}><Plus size={15} /> {t('routes.addClass')}</button>
        </div>
      ))}

      <button className="btn" style={{ marginTop: 14 }} onClick={() => upd([...data.routes, { ...NEW_ROUTE, classes: [] }])}>
        <Plus size={15} /> {t('routes.addRoute')}
      </button>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', margin: '24px 0 40px' }}>
        <button className="btn btn-primary btn-lg" disabled={saving} onClick={save}>
          {saving ? <Loader2 size={16} className="spinning" /> : t('routes.save')}
        </button>
        {saved && <span style={{ color: 'var(--brand-success)' }}>{t('routes.saved')}</span>}
      </div>
    </div>
  )
}
