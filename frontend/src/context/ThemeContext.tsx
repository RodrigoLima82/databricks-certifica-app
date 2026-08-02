import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react'
import type { Theme } from '@/types'
import { getTheme, setTenantSlug, clearTenantSlug } from '@/services/api'
import { useAuth } from '@/context/AuthContext'

interface ThemeCtx {
  theme: Theme | null
  slug: string
  loadTheme: (slug: string) => Promise<Theme | null>
  clearTheme: () => void
}

const Ctx = createContext<ThemeCtx>(null as any)
export const useTheme = () => useContext(Ctx)

function apply(theme: Theme | null) {
  const root = document.documentElement
  if (theme?.primary_color) root.style.setProperty('--brand-primary', theme.primary_color)
  else root.style.removeProperty('--brand-primary')   // vuelve al default neutro de :root
  document.title = theme ? `${theme.name} · Certifica` : 'Certifica'
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [theme, setTheme] = useState<Theme | null>(null)
  const [slug, setSlug] = useState<string>('')

  const loadTheme = useCallback(async (s: string): Promise<Theme | null> => {
    if (!s) return null
    try {
      const t = await getTheme(s)
      setTheme(t); setSlug(s); setTenantSlug(s); apply(t)
      return t
    } catch { return null }
  }, [])

  const clearTheme = useCallback(() => { setTheme(null); setSlug(''); clearTenantSlug(); apply(null) }, [])

  // El branding se aplica solo para el usuario logueado (su tenant). Las pantallas
  // pre-login (Landing) quedan neutras; el login branded lo dispara la propia página
  // de tenant (/t/<slug>) vía loadTheme. Así la raíz nunca queda atada a un cliente.
  useEffect(() => {
    const s = user?.tenant_slug
    if (s && s !== 'platform') loadTheme(s)
    else apply(null)
  }, [user, loadTheme])

  return <Ctx.Provider value={{ theme, slug, loadTheme, clearTheme }}>{children}</Ctx.Provider>
}
