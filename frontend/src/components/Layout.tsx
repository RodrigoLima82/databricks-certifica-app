import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { LayoutGrid, History, Shield, LogOut, Compass, Map } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { useT } from '@/i18n'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import ColorModeToggle from '@/components/ColorModeToggle'
import MobileNav from '@/components/MobileNav'
import MobileMenu from '@/components/MobileMenu'
import './Layout.css'

export default function Layout() {
  const location = useLocation()
  const { user, logout } = useAuth()
  const { theme } = useTheme()
  const t = useT()

  return (
    <div className="gc-layout">
      <header className="gc-header">
        <Link to="/" className="gc-brand">
          {theme?.logo_url
            ? <img src={theme.logo_url} alt={theme.name} className="gc-logo-img" />
            : <span className="gc-brand-name">{theme?.name || 'Certifica'}</span>}
        </Link>

        <nav className="gc-nav" aria-label={t('nav.mainNav')}>
          <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
            <Compass size={16} /> {t('nav.program')}
          </NavLink>
          <NavLink to="/rutas" className={({ isActive }) => isActive ? 'active' : ''}>
            <Map size={16} /> {t('nav.routes')}
          </NavLink>
          <NavLink to="/simulacros" className={({ isActive }) => isActive ? 'active' : ''}>
            <LayoutGrid size={16} /> {t('nav.simulacros')}
          </NavLink>
          <NavLink to="/historico" className={({ isActive }) => isActive ? 'active' : ''}>
            <History size={16} /> {t('nav.myHistory')}
          </NavLink>
          {user?.is_admin && (
            <NavLink to="/admin" className={({ isActive }) => isActive ? 'active' : ''}>
              <Shield size={16} /> {t('nav.admin')}
            </NavLink>
          )}
        </nav>

        <div className="gc-header-right">
          <ColorModeToggle />
          <LanguageSwitcher compact />
          {user && (
            <>
              <span className="gc-user" title={user.email}>{user.name}</span>
              <button className="gc-logout" onClick={logout} title={t('nav.logout')}>
                <LogOut size={17} />
              </button>
            </>
          )}
        </div>

        <MobileMenu />
      </header>

      <main className="gc-main">
        {location.pathname.startsWith('/cert/') && (
          <Link to="/simulacros" className="gc-back">{t('nav.allCerts')}</Link>
        )}
        <div className="gc-content page">
          <Outlet />
        </div>
      </main>

      <footer className="gc-footer">
        {t('nav.footer', { name: theme?.name ?? 'Certifica' })}
      </footer>

      <MobileNav />
    </div>
  )
}
