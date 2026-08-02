import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Users, ListChecks, Award, Pencil, Power, PowerOff, Trash2, Loader2, UserPlus, Activity,
} from 'lucide-react'
import {
  getAdminOverview, adminCreateUser, adminUpdateUser, adminSetUserStatus,
  adminSetUserPassword, adminDeleteUser,
} from '@/services/api'
import { useT, useI18n } from '@/i18n'
import type { AdminUserRow } from '@/types'
import './History.css'

const LOCALE = { es: 'es-CL', pt: 'pt-BR', en: 'en-US' } as const

function EditModal({ user, onClose }: { user: AdminUserRow; onClose: () => void }) {
  const t = useT(); const qc = useQueryClient()
  const [name, setName] = useState(user.name)
  const [area, setArea] = useState(user.area ?? '')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: async () => {
      await adminUpdateUser(user.email, { name: name.trim(), area: area.trim() })
      if (pw) await adminSetUserPassword(user.email, pw)
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-overview'] }); onClose() },
    onError: (e: any) => setErr(e?.response?.data?.detail ?? 'Error'),
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card card" onClick={e => e.stopPropagation()}>
        <h3>{t('admin.editUser')}</h3>
        <p className="muted" style={{ marginBottom: 12 }}>{user.email}</p>
        <label>{t('admin.name')}<input value={name} onChange={e => setName(e.target.value)} /></label>
        <label>{t('admin.area')}<input value={area} onChange={e => setArea(e.target.value)} placeholder="—" /></label>
        <label>{t('admin.newPassword')}<input type="password" value={pw} onChange={e => setPw(e.target.value)} placeholder="••••••" /></label>
        {err && <div className="login-error">{err}</div>}
        <div className="modal-actions">
          <button className="btn" onClick={onClose}>{t('admin.cancel')}</button>
          <button className="btn btn-primary" disabled={save.isPending} onClick={() => { setErr(null); save.mutate() }}>
            {save.isPending ? <Loader2 size={15} className="spinning" /> : t('admin.save')}
          </button>
        </div>
      </div>
    </div>
  )
}

function NewUserModal({ onClose }: { onClose: () => void }) {
  const t = useT(); const qc = useQueryClient()
  const [f, setF] = useState({ name: '', email: '', password: '', area: '', is_admin: false })
  const [err, setErr] = useState<string | null>(null)
  const create = useMutation({
    mutationFn: () => adminCreateUser({ ...f, area: f.area.trim() || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-overview'] }); onClose() },
    onError: (e: any) => setErr(e?.response?.data?.detail ?? t('admin.createError')),
  })
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card card" onClick={e => e.stopPropagation()}>
        <h3>{t('admin.newUser')}</h3>
        <label>{t('admin.name')}<input value={f.name} onChange={e => setF({ ...f, name: e.target.value })} /></label>
        <label>{t('admin.email')}<input type="email" value={f.email} onChange={e => setF({ ...f, email: e.target.value })} /></label>
        <label>{t('admin.password')}<input type="password" value={f.password} onChange={e => setF({ ...f, password: e.target.value })} /></label>
        <label>{t('admin.area')}<input value={f.area} onChange={e => setF({ ...f, area: e.target.value })} placeholder="—" /></label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14 }}>
          <input type="checkbox" checked={f.is_admin} onChange={e => setF({ ...f, is_admin: e.target.checked })} style={{ width: 'auto' }} />
          {t('admin.makeAdmin')}
        </label>
        {err && <div className="login-error">{err}</div>}
        <div className="modal-actions">
          <button className="btn" onClick={onClose}>{t('admin.cancel')}</button>
          <button className="btn btn-primary" disabled={create.isPending} onClick={() => { setErr(null); create.mutate() }}>
            {create.isPending ? <Loader2 size={15} className="spinning" /> : t('admin.createUser')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Admin() {
  const navigate = useNavigate()
  const t = useT()
  const { lang } = useI18n()
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['admin-overview'], queryFn: getAdminOverview })
  const [editing, setEditing] = useState<AdminUserRow | null>(null)
  const [creating, setCreating] = useState(false)

  const status = useMutation({
    mutationFn: ({ email, s }: { email: string; s: 'active' | 'suspended' }) => adminSetUserStatus(email, s),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-overview'] }),
  })
  const del = useMutation({
    mutationFn: (email: string) => adminDeleteUser(email),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-overview'] }),
  })

  if (isLoading) return <div className="spinner" />
  if (!data) return <p className="muted">{t('admin.noData')}</p>

  const fmt = (s?: string) => s ? new Date(s).toLocaleString(LOCALE[lang]) : '—'
  const score = (v?: number) => v == null ? '—' : `${v}%`
  const stop = (e: React.MouseEvent) => e.stopPropagation()

  return (
    <div>
      <div className="au-title-row">
        <div>
          <h1 className="hist-title">{t('admin.title')}</h1>
          <p className="muted hist-sub">{t('admin.sub', { m: data.pass_mark })}</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn" onClick={() => navigate('/admin/activity')}>
            <Activity size={16} /> {t('admin.activityLog')}
          </button>
          <button className="btn btn-primary" onClick={() => setCreating(true)}>
            <UserPlus size={16} /> {t('admin.newUser')}
          </button>
        </div>
      </div>

      <div className="adm-kpis">
        <div className="card adm-kpi"><Users size={20} color="var(--brand-primary)" /><div><b>{data.total_users}</b><span>{t('admin.users')}</span></div></div>
        <div className="card adm-kpi"><ListChecks size={20} color="var(--brand-primary)" /><div><b>{data.total_attempts}</b><span>{t('admin.attempts')}</span></div></div>
        <div className="card adm-kpi"><Award size={20} color="var(--brand-primary)" /><div><b>{data.users.filter(u => u.passed_any).length}</b><span>{t('admin.approvedCount')}</span></div></div>
      </div>

      <div className="card hist-table-wrap">
        <table className="hist-table">
          <thead>
            <tr><th>{t('admin.name')}</th><th>{t('admin.area')}</th><th>{t('admin.status')}</th><th>{t('admin.attempts')}</th><th>{t('admin.best')}</th><th>{t('admin.lastAccess')}</th><th>{t('admin.actions')}</th></tr>
          </thead>
          <tbody>
            {data.users.map(u => (
              <tr key={u.email}
                  className={u.attempts > 0 ? 'adm-row-click' : ''}
                  onClick={() => u.attempts > 0 && navigate(`/admin/user/${encodeURIComponent(u.email)}`)}
                  title={u.attempts > 0 ? t('admin.viewAttempts') : t('admin.noAttempts')}>
                <td>
                  <b>{u.name}</b>{u.is_admin && <span className="badge badge-associate" style={{ marginLeft: 6 }}>{t('admin.roleAdmin')}</span>}
                  <div className="muted" style={{ fontSize: 12 }}>{u.email}</div>
                </td>
                <td>{u.area || '—'}</td>
                <td><span className={`hist-badge ${u.status === 'active' ? 'ok' : 'no'}`}>
                  {u.status === 'active' ? t('admin.active') : t('admin.suspended')}</span></td>
                <td>{u.attempts}</td>
                <td>{score(u.best_score)}</td>
                <td>{fmt(u.last_attempt_at)}</td>
                <td onClick={stop}>
                  <span className="adm-actions">
                    <button className="link-btn" title={t('admin.edit')} onClick={() => setEditing(u)}><Pencil size={15} /></button>
                    <button className="link-btn" title={u.status === 'active' ? t('admin.suspend') : t('admin.activate')}
                      disabled={status.isPending}
                      onClick={() => status.mutate({ email: u.email, s: u.status === 'active' ? 'suspended' : 'active' })}>
                      {u.status === 'active' ? <PowerOff size={15} /> : <Power size={15} />}
                    </button>
                    <button className="link-btn" title={t('admin.deleteUser')} disabled={del.isPending}
                      onClick={() => { if (confirm(t('admin.confirmDelete', { name: u.name }))) del.mutate(u.email) }}>
                      <Trash2 size={15} />
                    </button>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && <EditModal user={editing} onClose={() => setEditing(null)} />}
      {creating && <NewUserModal onClose={() => setCreating(false)} />}
    </div>
  )
}
