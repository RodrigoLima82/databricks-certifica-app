import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import type { UserPublic } from '@/types'
import {
  getToken, setToken, clearToken, getMe,
  login as apiLogin, register as apiRegister,
} from '@/services/api'

interface AuthCtx {
  user: UserPublic | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
  setUser: (u: UserPublic) => void
}

const Ctx = createContext<AuthCtx>(null as any)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) { setLoading(false); return }
    getMe().then(setUser).catch(() => clearToken()).finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const r = await apiLogin(email, password)
    setToken(r.access_token); setUser(r.user)
  }
  const register = async (name: string, email: string, password: string) => {
    const r = await apiRegister(name, email, password)
    setToken(r.access_token); setUser(r.user)
  }
  const logout = () => { clearToken(); setUser(null) }

  return (
    <Ctx.Provider value={{ user, loading, login, register, logout, setUser }}>
      {children}
    </Ctx.Provider>
  )
}
