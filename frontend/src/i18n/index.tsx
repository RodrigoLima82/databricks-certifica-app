import { createContext, useContext, useState, ReactNode, useCallback } from 'react'
import { es } from './locales/es'
import { pt } from './locales/pt'
import { en } from './locales/en'

export type Lang = 'es' | 'pt' | 'en'
export const LANGS: { code: Lang; label: string }[] = [
  { code: 'es', label: 'Español' },
  { code: 'pt', label: 'Português' },
  { code: 'en', label: 'English' },
]

const DICTS: Record<Lang, any> = { es, pt, en }
const LANG_KEY = 'certifica_lang'

function detect(): Lang {
  const saved = localStorage.getItem(LANG_KEY) as Lang | null
  if (saved && DICTS[saved]) return saved
  const nav = (navigator.language || 'pt').slice(0, 2)
  return (['es', 'pt', 'en'].includes(nav) ? nav : 'pt') as Lang
}

function lookup(dict: any, key: string): string | undefined {
  return key.split('.').reduce((o, k) => (o == null ? o : o[k]), dict)
}

interface I18nCtx {
  lang: Lang
  setLang: (l: Lang) => void
  t: (key: string, vars?: Record<string, string | number>) => string
}

const Ctx = createContext<I18nCtx>(null as any)
export const useI18n = () => useContext(Ctx)
export const useT = () => useContext(Ctx).t

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(detect())

  const setLang = useCallback((l: Lang) => {
    localStorage.setItem(LANG_KEY, l)
    document.documentElement.lang = l === 'pt' ? 'pt-BR' : l === 'en' ? 'en' : 'es-CL'
    setLangState(l)
  }, [])

  const t = useCallback((key: string, vars?: Record<string, string | number>): string => {
    let s = lookup(DICTS[lang], key) ?? lookup(DICTS.pt, key) ?? key
    if (vars) for (const k of Object.keys(vars)) s = s.replace(new RegExp(`\\{${k}\\}`, 'g'), String(vars[k]))
    return s
  }, [lang])

  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>
}
