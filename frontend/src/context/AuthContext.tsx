import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import type { UserPublic, SignupPayload } from '@/types'
import {
  getToken, setToken, clearToken, getMe, setTenantSlug,
  login as apiLogin, register as apiRegister, signup as apiSignup,
} from '@/services/api'

interface AuthCtx {
  user: UserPublic | null
  loading: boolean
  login: (slug: string, email: string, password: string) => Promise<void>
  register: (slug: string, name: string, email: string, password: string) => Promise<void>
  signup: (payload: SignupPayload) => Promise<void>
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

  const finish = (r: { access_token: string; user: UserPublic }) => {
    setToken(r.access_token)
    if (r.user.tenant_slug) setTenantSlug(r.user.tenant_slug)
    setUser(r.user)
  }

  const login = async (slug: string, email: string, password: string) =>
    finish(await apiLogin(slug, email, password))
  const register = async (slug: string, name: string, email: string, password: string) =>
    finish(await apiRegister(slug, name, email, password))
  const signup = async (payload: SignupPayload) =>
    finish(await apiSignup(payload))
  const logout = () => { clearToken(); setUser(null) }

  return (
    <Ctx.Provider value={{ user, loading, login, register, signup, logout, setUser }}>
      {children}
    </Ctx.Provider>
  )
}
