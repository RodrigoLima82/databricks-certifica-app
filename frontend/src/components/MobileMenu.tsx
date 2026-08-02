import { useState } from 'react'
import { Menu, X, Sun, Moon, SunMoon, LogOut, Globe } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useColorMode, ColorMode } from '@/context/ColorModeContext'
import { useI18n, LANGS, Lang } from '@/i18n'
import { useT } from '@/i18n'
import './MobileMenu.css'

/**
 * Menu "sanduíche" para mobile — botão hamburger no header que abre um drawer
 * com: idioma (botões grandes), aparência (claro/escuro/auto) e sair.
 * Renderiza sempre no DOM; o CSS o oculta no desktop (>768px).
 */
export default function MobileMenu() {
  const [open, setOpen] = useState(false)
  const { user, logout } = useAuth()
  const { mode, setMode } = useColorMode()
  const { lang, setLang } = useI18n()
  const t = useT()

  const modes: { key: ColorMode; icon: JSX.Element; label: string }[] = [
    { key: 'light', icon: <Sun size={18} />, label: t('menu.light') },
    { key: 'dark', icon: <Moon size={18} />, label: t('menu.dark') },
    { key: 'auto', icon: <SunMoon size={18} />, label: t('menu.auto') },
  ]

  return (
    <>
      <button className="mm-trigger" aria-label={t('menu.open')} aria-expanded={open}
              onClick={() => setOpen(true)}>
        <Menu size={22} />
      </button>

      {open && (
        <div className="mm-overlay" onClick={() => setOpen(false)}>
          <div className="mm-panel" role="dialog" aria-label={t('menu.settings')}
               onClick={e => e.stopPropagation()}>
            <div className="mm-head">
              <span className="mm-title">{t('menu.settings')}</span>
              <button className="mm-close" aria-label={t('menu.close')} onClick={() => setOpen(false)}>
                <X size={20} />
              </button>
            </div>

            {user && (
              <div className="mm-user">
                <b>{user.name}</b>
                <span>{user.email}</span>
              </div>
            )}

            <div className="mm-section">
              <div className="mm-label"><Globe size={15} /> {t('menu.language')}</div>
              <div className="mm-choices">
                {LANGS.map(l => (
                  <button key={l.code}
                          className={l.code === lang ? 'mm-choice active' : 'mm-choice'}
                          onClick={() => setLang(l.code as Lang)}>
                    {l.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="mm-section">
              <div className="mm-label"><SunMoon size={15} /> {t('menu.appearance')}</div>
              <div className="mm-choices">
                {modes.map(m => (
                  <button key={m.key}
                          className={m.key === mode ? 'mm-choice active' : 'mm-choice'}
                          onClick={() => setMode(m.key)}>
                    {m.icon} {m.label}
                  </button>
                ))}
              </div>
            </div>

            {user && (
              <button className="mm-logout" onClick={() => { setOpen(false); logout() }}>
                <LogOut size={17} /> {t('nav.logout')}
              </button>
            )}
          </div>
        </div>
      )}
    </>
  )
}
