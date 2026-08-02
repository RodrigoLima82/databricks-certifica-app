import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, Building2 } from 'lucide-react'
import { useTheme } from '@/context/ThemeContext'
import { useT } from '@/i18n'
import { resolveTenant } from '@/services/api'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import './Login.css'

export default function Landing() {
  const { clearTheme } = useTheme()
  const navigate = useNavigate()
  const t = useT()
  const [slug, setSlug] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // raíz neutra: limpia cualquier branding de tenant recordado
  useEffect(() => { clearTheme() }, [clearTheme])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null); setLoading(true)
    try {
      const { slug: resolved } = await resolveTenant(slug.trim())   // por nombre o slug
      navigate(`/t/${resolved}`)   // entra al login branded del tenant
    } catch {
      setError(t('landing.notFound'))
    } finally { setLoading(false) }
  }

  return (
    <div className="login-page">
      <div className="login-langs"><LanguageSwitcher /></div>
      <div className="login-card card">
        <div className="login-brand"><span className="login-brand-name">Certifica</span></div>
        <p className="login-sub"><Building2 size={15} /> {t('landing.subtitle')}</p>
        <form onSubmit={submit} className="login-form">
          <label>
            {t('landing.spaceId')}
            <input value={slug} onChange={e => setSlug(e.target.value)}
              placeholder={t('landing.spacePlaceholder')} required autoFocus />
          </label>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" className="btn btn-primary btn-lg login-submit" disabled={loading}>
            {loading ? <><Loader2 size={18} className="spinning" /> {t('landing.searching')}</> : t('landing.continue')}
          </button>
        </form>
        <p className="login-foot">
          {t('landing.newCompany')} <a href="/signup">{t('landing.createSpace')}</a>.
        </p>
      </div>
    </div>
  )
}
