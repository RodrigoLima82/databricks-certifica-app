import { Languages } from 'lucide-react'
import { useI18n, LANGS, Lang } from '@/i18n'

export default function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { lang, setLang } = useI18n()
  return (
    <span className="lang-switch" title="Idioma / Language">
      <Languages size={15} />
      <select value={lang} onChange={e => setLang(e.target.value as Lang)} aria-label="Idioma">
        {LANGS.map(l => <option key={l.code} value={l.code}>{compact ? l.code.toUpperCase() : l.label}</option>)}
      </select>
    </span>
  )
}
