import { useState } from 'react'
import { Loader2, Rocket } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useT } from '@/i18n'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import './Login.css'

export default function Signup() {
  const { signup } = useAuth()
  const t = useT()
  const [company, setCompany] = useState('')
  const [slug, setSlug] = useState('')
  const [color, setColor] = useState('#EC0000')
  const [adminName, setAdminName] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [adminPassword, setAdminPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const slugify = (s: string) =>
    s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null); setLoading(true)
    try {
      await signup({
        company: company.trim(), slug: slug || slugify(company),
        primary_color: color, admin_name: adminName.trim(),
        admin_email: adminEmail.trim(), admin_password: adminPassword,
      })
      window.location.assign('/')
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? t('signup.error'))
    } finally { setLoading(false) }
  }

  return (
    <div className="login-page">
      <div className="login-langs"><LanguageSwitcher /></div>
      <div className="login-card card" style={{ maxWidth: 460 }}>
        <div className="login-brand"><span className="login-brand-name">Certifica</span></div>
        <p className="login-sub"><Rocket size={15} /> {t('signup.title')}</p>
        <form onSubmit={submit} className="login-form">
          <label>
            {t('signup.company')}
            <input value={company} onChange={e => { setCompany(e.target.value); if (!slug) setSlug(slugify(e.target.value)) }}
              placeholder={t('signup.companyPlaceholder')} required autoFocus />
          </label>
          <label>
            {t('signup.slug')}
            <input value={slug} onChange={e => setSlug(slugify(e.target.value))} placeholder={t('signup.slugPlaceholder')} required />
          </label>
          <label>
            {t('signup.brandColor')}
            <input type="color" value={color} onChange={e => setColor(e.target.value)} style={{ height: 40, padding: 4 }} />
          </label>
          <label>
            {t('signup.yourNameAdmin')}
            <input value={adminName} onChange={e => setAdminName(e.target.value)} required />
          </label>
          <label>
            {t('signup.adminEmail')}
            <input type="email" value={adminEmail} onChange={e => setAdminEmail(e.target.value)}
              placeholder={t('signup.adminEmailPlaceholder')} required />
          </label>
          <label>
            {t('signup.password')}
            <input type="password" value={adminPassword} onChange={e => setAdminPassword(e.target.value)}
              placeholder="••••••••" required minLength={6} />
          </label>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" className="btn btn-primary btn-lg login-submit" disabled={loading}>
            {loading ? <><Loader2 size={18} className="spinning" /> {t('signup.creating')}</> : t('signup.createAndEnter')}
          </button>
        </form>
        <p className="login-foot"><a href="/">{t('common.back')}</a></p>
      </div>
    </div>
  )
}
