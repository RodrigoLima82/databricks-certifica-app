import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { LayoutGrid, History, Shield, LogOut } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import './Layout.css'

export default function Layout() {
  const location = useLocation()
  const isHome = location.pathname === '/'
  const { user, logout } = useAuth()

  return (
    <div className="gc-layout">
      <header className="gc-header">
        <Link to="/" className="gc-brand">
          <img src="/databricks-logo.svg" alt="Databricks" className="gc-logo-img" />
          <span className="gc-brand-name">Certifica</span>
        </Link>

        <nav className="gc-nav">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
            <LayoutGrid size={16} /> Certificações
          </NavLink>
          <NavLink to="/historico" className={({ isActive }) => isActive ? 'active' : ''}>
            <History size={16} /> Meu histórico
          </NavLink>
          {user?.is_admin && (
            <NavLink to="/admin" className={({ isActive }) => isActive ? 'active' : ''}>
              <Shield size={16} /> Admin
            </NavLink>
          )}
        </nav>

        <div className="gc-header-right">
          {user && (
            <>
              <span className="gc-user" title={user.email}>{user.name}</span>
              <button className="gc-logout" onClick={logout} title="Sair">
                <LogOut size={17} />
              </button>
            </>
          )}
        </div>
      </header>

      <main className="gc-main">
        {!isHome && (
          <Link to="/" className="gc-back">← Todas as certificações</Link>
        )}
        <div className="gc-content page">
          <Outlet />
        </div>
      </main>

      <footer className="gc-footer">
        Databricks Certifica · Preparação para certificações Databricks · As questões deste
        simulador são de prática e não refletem o exame oficial.
      </footer>
    </div>
  )
}
