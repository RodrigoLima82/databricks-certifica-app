import { Sun, Moon, SunMoon } from 'lucide-react'
import { useColorMode, ColorMode } from '@/context/ColorModeContext'
import { useT } from '@/i18n'

/**
 * Toggle compacto de tema para o header desktop: cicla claro → escuro → auto.
 * No mobile isso vive no MobileMenu (drawer); aqui é escondido via CSS.
 */
const ORDER: ColorMode[] = ['light', 'dark', 'auto']

export default function ColorModeToggle() {
  const { mode, setMode } = useColorMode()
  const t = useT()
  const next = () => setMode(ORDER[(ORDER.indexOf(mode) + 1) % ORDER.length])
  const icon = mode === 'light' ? <Sun size={16} /> : mode === 'dark' ? <Moon size={16} /> : <SunMoon size={16} />
  const label = mode === 'light' ? t('menu.light') : mode === 'dark' ? t('menu.dark') : t('menu.auto')

  return (
    <button className="gc-mode-toggle" onClick={next} title={`${t('menu.appearance')}: ${label}`}
            aria-label={`${t('menu.appearance')}: ${label}`}>
      {icon}
    </button>
  )
}
