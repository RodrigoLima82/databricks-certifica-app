import { useState, useEffect, useCallback } from 'react'
import {
  X, Compass, Map, LayoutGrid, Sparkles, History, Settings2, GraduationCap,
} from 'lucide-react'
import { useT, useI18n } from '@/i18n'
import { useTheme } from '@/context/ThemeContext'
import './Tour.css'

const SEEN_KEY = 'certifica_tour_seen'

/** Passos do tour. Cada um: ícone + chaves i18n (título/corpo). */
const STEPS = [
  { icon: GraduationCap, title: 'tour.welcomeTitle', body: 'tour.welcomeBody' },
  { icon: Compass, title: 'tour.programTitle', body: 'tour.programBody' },
  { icon: Map, title: 'tour.routesTitle', body: 'tour.routesBody' },
  { icon: LayoutGrid, title: 'tour.practiceTitle', body: 'tour.practiceBody' },
  { icon: Sparkles, title: 'tour.studyTitle', body: 'tour.studyBody' },
  { icon: History, title: 'tour.historyTitle', body: 'tour.historyBody' },
  { icon: Settings2, title: 'tour.langTitle', body: 'tour.langBody' },
]

/** Dispara a abertura do tour de qualquer lugar (ex.: menu mobile). */
export const OPEN_TOUR_EVENT = 'certifica:open-tour'
export const openTourEvent = () => window.dispatchEvent(new Event(OPEN_TOUR_EVENT))

export function useTour() {
  const [open, setOpen] = useState(false)
  const openTour = useCallback(() => setOpen(true), [])
  const closeTour = useCallback(() => {
    localStorage.setItem(SEEN_KEY, '1')
    setOpen(false)
  }, [])
  // Abre automaticamente no primeiro acesso (uma vez por navegador) e escuta o
  // evento global (para o menu mobile reabrir o tutorial).
  useEffect(() => {
    if (!localStorage.getItem(SEEN_KEY)) setOpen(true)
    const handler = () => setOpen(true)
    window.addEventListener(OPEN_TOUR_EVENT, handler)
    return () => window.removeEventListener(OPEN_TOUR_EVENT, handler)
  }, [])
  return { open, openTour, closeTour }
}

export default function Tour({ open, onClose }: { open: boolean; onClose: () => void }) {
  const t = useT()
  const { lang } = useI18n()
  const { theme } = useTheme()
  const [i, setI] = useState(0)

  // Reinicia no passo 0 sempre que reabrir.
  useEffect(() => { if (open) setI(0) }, [open])

  // Fecha com Esc; setas navegam.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      else if (e.key === 'ArrowRight') setI(v => Math.min(v + 1, STEPS.length - 1))
      else if (e.key === 'ArrowLeft') setI(v => Math.max(v - 1, 0))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  const step = STEPS[i]
  const Icon = step.icon
  const isLast = i === STEPS.length - 1
  const name = theme?.name || 'Certifica'
  void lang // re-render ao trocar idioma

  return (
    <div className="tour-overlay" onClick={onClose}>
      <div className="tour-card" role="dialog" aria-modal="true" aria-label={t('tour.title')}
           onClick={e => e.stopPropagation()}>
        <button className="tour-close" aria-label={t('tour.skip')} onClick={onClose}>
          <X size={18} />
        </button>

        <div className="tour-icon"><Icon size={30} /></div>
        <h2 className="tour-title">{t(step.title, { name })}</h2>
        <p className="tour-body">{t(step.body, { name })}</p>

        <div className="tour-dots" role="tablist">
          {STEPS.map((_, k) => (
            <button key={k} className={k === i ? 'tour-dot active' : 'tour-dot'}
                    aria-label={t('tour.step', { i: k + 1, n: STEPS.length })}
                    aria-selected={k === i} onClick={() => setI(k)} />
          ))}
        </div>

        <div className="tour-actions">
          <span className="tour-step">{t('tour.step', { i: i + 1, n: STEPS.length })}</span>
          <div className="tour-btns">
            {i > 0 && (
              <button className="btn tour-btn-ghost" onClick={() => setI(i - 1)}>
                {t('tour.back')}
              </button>
            )}
            {isLast ? (
              <button className="btn btn-primary" onClick={onClose}>{t('tour.done')}</button>
            ) : (
              <button className="btn btn-primary" onClick={() => setI(i + 1)}>{t('tour.next')}</button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
