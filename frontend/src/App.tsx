import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import Layout from '@/components/Layout'
import Login from '@/pages/Login'
import Home from '@/pages/Home'
import CertDetail from '@/pages/CertDetail'
import History from '@/pages/History'
import Admin from '@/pages/Admin'
import AdminUser from '@/pages/AdminUser'

function Gate() {
  const { user, loading } = useAuth()
  if (loading) return <div className="spinner" />
  if (!user) return <Login />
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="cert/:id" element={<CertDetail />} />
        <Route path="historico" element={<History />} />
        {user.is_admin && <Route path="admin" element={<Admin />} />}
        {user.is_admin && <Route path="admin/user/:email" element={<AdminUser />} />}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Gate />
    </BrowserRouter>
  )
}
