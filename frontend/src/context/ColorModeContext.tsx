import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react'

/**
 * Modo de cor claro/escuro (independente do branding do tenant).
 * - 'light' | 'dark' : forçado pelo usuário
 * - 'auto'           : segue o sistema (prefers-color-scheme)
 * Persistido em localStorage. Aplica [data-theme] no <html>.
 */
export type ColorMode = 'light' | 'dark' | 'auto'

interface ColorModeCtx {
  mode: ColorMode
  setMode: (m: ColorMode) => void
  resolved: 'light' | 'dark'   // o tema efetivamente aplicado
}

const Ctx = createContext<ColorModeCtx>(null as any)
export const useColorMode = () => useContext(Ctx)

const KEY = 'certifica-color-mode'
const mq = () => window.matchMedia('(prefers-color-scheme: dark)')

function resolve(mode: ColorMode): 'light' | 'dark' {
  if (mode === 'auto') return mq().matches ? 'dark' : 'light'
  return mode
}

function applyToDom(resolved: 'light' | 'dark') {
  document.documentElement.setAttribute('data-theme', resolved)
}

export function ColorModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ColorMode>(() => {
    const saved = localStorage.getItem(KEY) as ColorMode | null
    return saved && ['light', 'dark', 'auto'].includes(saved) ? saved : 'light'
  })
  const [resolved, setResolved] = useState<'light' | 'dark'>(() => resolve(mode))

  const setMode = useCallback((m: ColorMode) => {
    localStorage.setItem(KEY, m)
    setModeState(m)
  }, [])

  useEffect(() => {
    const r = resolve(mode)
    setResolved(r)
    applyToDom(r)
    // em 'auto', reage a mudanças do sistema
    if (mode !== 'auto') return
    const m = mq()
    const onChange = () => { const rr = resolve('auto'); setResolved(rr); applyToDom(rr) }
    m.addEventListener('change', onChange)
    return () => m.removeEventListener('change', onChange)
  }, [mode])

  return <Ctx.Provider value={{ mode, setMode, resolved }}>{children}</Ctx.Provider>
}
