import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { setTenantSlug } from '@/services/api'
import Layout from '@/components/Layout'
import Login from '@/pages/Login'
import Landing from '@/pages/Landing'
import Signup from '@/pages/Signup'
import Platform from '@/pages/Platform'
import Home from '@/pages/Home'
import Program from '@/pages/Program'
import ProgramEditor from '@/pages/ProgramEditor'
import RoutesPage from '@/pages/Routes'
import RoutesEditor from '@/pages/RoutesEditor'
import CertDetail from '@/pages/CertDetail'
import History from '@/pages/History'
import Admin from '@/pages/Admin'
import AdminUser from '@/pages/AdminUser'
import AdminActivity from '@/pages/AdminActivity'

const Spinner = () => <div className="spinner" />

// /t/:slug — entrada branded del tenant: fija el slug y muestra su login.
// Si ya está logueado, va a la app.
function TenantEntry() {
  const { slug = '' } = useParams()
  const { user, loading } = useAuth()
  useEffect(() => { setTenantSlug(slug.toLowerCase()) }, [slug])
  if (loading) return <Spinner />
  if (user) return <Navigate to="/" replace />
  return <Login fixedSlug={slug.toLowerCase()} />
}

// /platform — consola do superadmin (login no tenant 'platform')
function PlatformGate() {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  if (user?.is_superadmin) return <Platform />
  return <Login fixedSlug="platform" />
}

// app principal (tenant) com gating de auth
function AppGate() {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  if (!user) return <Landing />   // raíz neutra: selector de empresa (multi-tenant)
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Program />} />
        <Route path="simulacros" element={<Home />} />
        <Route path="rutas" element={<RoutesPage />} />
        <Route path="rutas/editar" element={<RoutesEditor />} />
        <Route path="programa/editar" element={<ProgramEditor />} />
        <Route path="cert/:id" element={<CertDetail />} />
        <Route path="historico" element={<History />} />
        {user.is_admin && <Route path="admin" element={<Admin />} />}
        {user.is_admin && <Route path="admin/activity" element={<AdminActivity />} />}
        {user.is_admin && <Route path="admin/user/:email" element={<AdminUser />} />}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/signup" element={<Signup />} />
        <Route path="/platform" element={<PlatformGate />} />
        <Route path="/t/:slug" element={<TenantEntry />} />
        <Route path="/*" element={<AppGate />} />
      </Routes>
    </BrowserRouter>
  )
}
