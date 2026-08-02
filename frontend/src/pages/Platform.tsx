import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, Plus, LogOut, Loader2, Users, ListChecks, Power, PowerOff, ExternalLink, UserCog, Trash2, Pencil, BookOpen, Map as MapIcon } from 'lucide-react'
import {
  listTenants, createTenant, setTenantStatus, updateTenantBranding,
  listOperators, createOperator, deleteOperator,
} from '@/services/api'
import { useAuth } from '@/context/AuthContext'
import { useT } from '@/i18n'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import type { TenantPublic, Operator } from '@/types'
import './History.css'

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(r.result as string)
    r.onerror = reject
    r.readAsDataURL(file)
  })
}

function EditTenantModal({ tenant, onClose }: { tenant: TenantPublic; onClose: () => void }) {
  const t = useT(); const qc = useQueryClient()
  const [name, setName] = useState(tenant.name)
  const [color, setColor] = useState(tenant.primary_color)
  const [logo, setLogo] = useState<string | undefined>(tenant.logo_url || undefined)
  const save = useMutation({
    mutationFn: () => updateTenantBranding(tenant.slug, { name, primary_color: color, logo_url: logo }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['tenants'] }); onClose() },
  })
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card card" onClick={e => e.stopPropagation()}>
        <h3>{t('platform.editTenant')} · {tenant.slug}</h3>
        <label>{t('platform.company')}<input value={name} onChange={e => setName(e.target.value)} /></label>
        <label>{t('platform.color')}<input type="color" value={color} onChange={e => setColor(e.target.value)} style={{ height: 40 }} /></label>
        <label>{t('platform.logo')}
          <input type="file" accept="image/svg+xml,image/png,image/jpeg"
            onChange={async e => { const f = e.target.files?.[0]; if (f) setLogo(await fileToDataUrl(f)) }} />
        </label>
        {logo && <img src={logo} alt="logo" style={{ maxHeight: 40, marginTop: 8 }} />}
        <div className="modal-actions">
          <button className="btn" onClick={onClose}>{t('platform.cancel')}</button>
          <button className="btn btn-primary" disabled={save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? <Loader2 size={15} className="spinning" /> : t('platform.save')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Platform() {
  const { logout } = useAuth()
  const t = useT()
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['tenants'], queryFn: listTenants })
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<TenantPublic | null>(null)
  const blank = { name: '', slug: '', primary_color: '#EC0000', logo_url: '',
    admin_email: '', admin_name: '', admin_password: '' }
  const [form, setForm] = useState(blank)
  const [error, setError] = useState<string | null>(null)

  const create = useMutation({
    mutationFn: () => createTenant({ ...form, logo_url: form.logo_url || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['tenants'] }); setOpen(false); setForm(blank) },
    onError: (e: any) => setError(e?.response?.data?.detail ?? t('platform.createError')),
  })

  const toggle = useMutation({
    mutationFn: ({ slug, status }: { slug: string; status: 'active' | 'suspended' }) => setTenantStatus(slug, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenants'] }),
  })

  // ── Operadores (usuários administrativos do console) ──
  const ops = useQuery({ queryKey: ['operators'], queryFn: listOperators })
  const [opOpen, setOpOpen] = useState(false)
  const [opForm, setOpForm] = useState({ name: '', email: '', password: '' })
  const [opErr, setOpErr] = useState<string | null>(null)
  const createOp = useMutation({
    mutationFn: () => createOperator(opForm),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['operators'] }); setOpOpen(false); setOpForm({ name: '', email: '', password: '' }) },
    onError: (e: any) => setOpErr(e?.response?.data?.detail ?? t('platform.opError')),
  })
  const delOp = useMutation({
    mutationFn: (email: string) => deleteOperator(email),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['operators'] }),
  })

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: 24 }}>
      <div className="au-title-row">
        <div>
          <h1 className="hist-title"><Building2 size={22} style={{ verticalAlign: -4 }} /> {t('platform.title')}</h1>
          <p className="muted hist-sub">{t('platform.sub')}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <LanguageSwitcher compact />
          <button className="btn btn-primary" onClick={() => { setError(null); setOpen(o => !o) }}>
            <Plus size={16} /> {t('platform.newTenant')}
          </button>
          <button className="btn" onClick={logout}><LogOut size={16} /> {t('platform.logout')}</button>
        </div>
      </div>

      {open && (
        <div className="card" style={{ padding: 18, marginBottom: 18, display: 'grid', gap: 10,
          gridTemplateColumns: 'repeat(2, 1fr)' }}>
          <label>{t('platform.company')}<input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></label>
          <label>{t('platform.slug')}<input value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value.toLowerCase() })} placeholder="acme" /></label>
          <label>{t('platform.color')}<input type="color" value={form.primary_color} onChange={e => setForm({ ...form, primary_color: e.target.value })} style={{ height: 38 }} /></label>
          <label>{t('platform.logo')}<input type="file" accept="image/svg+xml,image/png,image/jpeg"
            onChange={async e => { const f = e.target.files?.[0]; if (f) setForm({ ...form, logo_url: await fileToDataUrl(f) }) }} /></label>
          <label>{t('platform.adminEmail')}<input value={form.admin_email} onChange={e => setForm({ ...form, admin_email: e.target.value })} /></label>
          <label>{t('platform.adminName')}<input value={form.admin_name} onChange={e => setForm({ ...form, admin_name: e.target.value })} /></label>
          <label>{t('platform.adminPassword')}<input type="password" value={form.admin_password} onChange={e => setForm({ ...form, admin_password: e.target.value })} /></label>
          {error && <div className="login-error" style={{ gridColumn: '1 / -1' }}>{error}</div>}
          <button className="btn btn-primary" style={{ gridColumn: '1 / -1' }} disabled={create.isPending}
            onClick={() => { setError(null); create.mutate() }}>
            {create.isPending ? <><Loader2 size={16} className="spinning" /> {t('platform.creating')}</> : t('platform.createTenant')}
          </button>
        </div>
      )}

      <h3 style={{ margin: '6px 0 10px' }}>{t('platform.tenants')}</h3>
      {isLoading ? <div className="spinner" /> : (
        <div className="card hist-table-wrap">
          <table className="hist-table">
            <thead><tr><th>{t('platform.company')}</th><th>{t('platform.slug')}</th><th>{t('platform.color')}</th><th>{t('platform.users')}</th><th>{t('platform.attempts')}</th><th>{t('platform.status')}</th><th></th></tr></thead>
            <tbody>
              {data?.map((tn: TenantPublic) => (
                <tr key={tn.id}>
                  <td><b>{tn.name}</b></td>
                  <td className="muted">{tn.slug}</td>
                  <td><span style={{ display: 'inline-block', width: 16, height: 16, borderRadius: 4,
                    background: tn.primary_color, verticalAlign: -3 }} /> {tn.primary_color}</td>
                  <td><Users size={14} /> {tn.user_count}</td>
                  <td><ListChecks size={14} /> {tn.attempt_count}</td>
                  <td><span className={`hist-badge ${tn.status === 'active' ? 'ok' : 'no'}`}>{tn.status}</span></td>
                  <td>
                    {tn.slug !== 'platform' && (
                      <span style={{ display: 'inline-flex', gap: 12, alignItems: 'center' }}>
                        <a className="link-btn" href={`/t/${tn.slug}`} target="_blank" rel="noreferrer"
                          title={t('platform.openTitle')} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <ExternalLink size={15} /> {t('platform.open')}
                        </a>
                        <button className="link-btn" title={t('platform.edit')} onClick={() => setEditing(tn)}>
                          <Pencil size={15} />
                        </button>
                        <a className="link-btn" href={`/programa/editar?slug=${tn.slug}`} target="_blank" rel="noreferrer"
                          title={t('program.editProgram')}><BookOpen size={15} /></a>
                        <a className="link-btn" href={`/rutas/editar?slug=${tn.slug}`} target="_blank" rel="noreferrer"
                          title={t('routes.editRoutes')}><MapIcon size={15} /></a>
                        <button className="link-btn" disabled={toggle.isPending}
                          onClick={() => toggle.mutate({ slug: tn.slug, status: tn.status === 'active' ? 'suspended' : 'active' })}
                          title={tn.status === 'active' ? t('platform.suspend') : t('platform.activate')}>
                          {tn.status === 'active' ? <PowerOff size={16} /> : <Power size={16} />}
                        </button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="au-title-row" style={{ marginTop: 28 }}>
        <h3 style={{ margin: 0 }}><UserCog size={18} style={{ verticalAlign: -3 }} /> {t('platform.operators')}</h3>
        <button className="btn" onClick={() => { setOpErr(null); setOpOpen(o => !o) }}>
          <Plus size={15} /> {t('platform.newOperator')}
        </button>
      </div>
      {opOpen && (
        <div className="card" style={{ padding: 16, marginBottom: 14, display: 'grid', gap: 10,
          gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <label>{t('admin.name')}<input value={opForm.name} onChange={e => setOpForm({ ...opForm, name: e.target.value })} /></label>
          <label>{t('admin.email')}<input value={opForm.email} onChange={e => setOpForm({ ...opForm, email: e.target.value })} /></label>
          <label>{t('admin.password')}<input type="password" value={opForm.password} onChange={e => setOpForm({ ...opForm, password: e.target.value })} /></label>
          {opErr && <div className="login-error" style={{ gridColumn: '1 / -1' }}>{opErr}</div>}
          <button className="btn btn-primary" style={{ gridColumn: '1 / -1' }} disabled={createOp.isPending}
            onClick={() => { setOpErr(null); createOp.mutate() }}>
            {createOp.isPending ? <><Loader2 size={16} className="spinning" /> {t('platform.creating')}</> : t('platform.createOperator')}
          </button>
        </div>
      )}
      {editing && <EditTenantModal tenant={editing} onClose={() => setEditing(null)} />}

      {!ops.isLoading && (
        <div className="card hist-table-wrap">
          <table className="hist-table">
            <thead><tr><th>{t('admin.name')}</th><th>{t('admin.email')}</th><th></th></tr></thead>
            <tbody>
              {ops.data?.map((op: Operator) => (
                <tr key={op.email}>
                  <td><b>{op.name}</b></td>
                  <td className="muted">{op.email}</td>
                  <td>
                    <button className="link-btn" disabled={delOp.isPending}
                      title={t('platform.remove')}
                      onClick={() => { if (confirm(t('platform.confirmRemoveOperator', { name: op.name }))) delOp.mutate(op.email) }}>
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
