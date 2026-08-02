import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, GraduationCap } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { useT } from '@/i18n'
import { getTenantSlug } from '@/services/api'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import './Login.css'

export default function Login({ fixedSlug }: { fixedSlug?: string }) {
  const { login, register } = useAuth()
  const { theme, loadTheme, clearTheme } = useTheme()
  const navigate = useNavigate()
  const t = useT()
  const slug = fixedSlug || theme?.slug || getTenantSlug()
  const isPlatform = fixedSlug === 'platform'

  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { if (slug && !isPlatform) loadTheme(slug) }, [slug, isPlatform, loadTheme])

  const canRegister = !isPlatform && (theme?.allow_self_register ?? true)
  const brandName = isPlatform ? 'Plataforma' : (theme?.name ?? 'Certifica')
  const logo = theme?.logo_url

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null); setLoading(true)
    try {
      if (mode === 'register') await register(slug, name.trim(), email.trim(), password)
      else await login(slug, email.trim(), password)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? t('login.authError'))
    } finally { setLoading(false) }
  }

  return (
    <div className="login-page">
      <div className="login-langs"><LanguageSwitcher /></div>
      <div className="login-card card">
        <div className="login-brand">
          {logo
            ? <img src={logo} alt={brandName} className="login-logo" />
            : <span className="login-brand-name">{brandName}</span>}
        </div>
        <p className="login-sub">
          <GraduationCap size={15} /> {isPlatform ? t('login.platformSubtitle') : t('login.hubSubtitle')}
        </p>

        <div className="login-tabs">
          <button className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); setError(null) }}>
            {t('common.enter')}
          </button>
          {canRegister && (
            <button className={mode === 'register' ? 'active' : ''} onClick={() => { setMode('register'); setError(null) }}>
              {t('common.createAccount')}
            </button>
          )}
        </div>

        <form onSubmit={submit} className="login-form">
          {mode === 'register' && (
            <label>
              {t('login.fullName')}
              <input value={name} onChange={e => setName(e.target.value)}
                placeholder={t('login.yourName')} required autoComplete="name" />
            </label>
          )}
          <label>
            {t('login.email')}
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder={t('login.emailPlaceholder')} required autoComplete="email" />
          </label>
          <label>
            {t('login.password')}
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" required minLength={6}
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'} />
          </label>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="btn btn-primary btn-lg login-submit" disabled={loading}>
            {loading ? <><Loader2 size={18} className="spinning" /> {t('common.wait')}</>
              : mode === 'register' ? t('login.createAndEnter') : t('common.enter')}
          </button>
        </form>

        {!isPlatform && (
          <p className="login-foot">
            {t('login.noCompany')} <a href="/signup">{t('login.createSpace')}</a>.
            <br />
            <a href="#" onClick={e => { e.preventDefault(); clearTheme(); navigate('/') }}>{t('login.changeWorkspace')}</a>
          </p>
        )}
      </div>
    </div>
  )
}
