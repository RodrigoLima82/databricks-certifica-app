import { useState, useEffect, useCallback, useLayoutEffect } from 'react'
import {
  X, Compass, Map, LayoutGrid, Sparkles, History, Settings2, GraduationCap,
} from 'lucide-react'
import { useT, useI18n } from '@/i18n'
import { useTheme } from '@/context/ThemeContext'
import './Tour.css'

const SEEN_KEY = 'certifica_tour_seen'

/**
 * Passos do tour. `target` (opcional) = seletor CSS do elemento na tela a
 * destacar; sem target o passo aparece centralizado (boas-vindas, estudo com IA).
 */
const STEPS: { icon: any; title: string; body: string; target?: string }[] = [
  { icon: GraduationCap, title: 'tour.welcomeTitle', body: 'tour.welcomeBody' },
  { icon: Compass, title: 'tour.programTitle', body: 'tour.programBody', target: '[data-tour="program"]' },
  { icon: Map, title: 'tour.routesTitle', body: 'tour.routesBody', target: '[data-tour="routes"]' },
  { icon: LayoutGrid, title: 'tour.practiceTitle', body: 'tour.practiceBody', target: '[data-tour="practice"]' },
  { icon: Sparkles, title: 'tour.studyTitle', body: 'tour.studyBody', target: '[data-tour="practice"]' },
  { icon: History, title: 'tour.historyTitle', body: 'tour.historyBody', target: '[data-tour="history"]' },
  { icon: Settings2, title: 'tour.langTitle', body: 'tour.langBody', target: '[data-tour="settings"]' },
]

const PAD = 8          // respiro do recorte em volta do alvo
const GAP = 14         // distância entre o alvo e o balão
const CARD_W = 340

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
  useEffect(() => {
    if (!localStorage.getItem(SEEN_KEY)) setOpen(true)
    const handler = () => setOpen(true)
    window.addEventListener(OPEN_TOUR_EVENT, handler)
    return () => window.removeEventListener(OPEN_TOUR_EVENT, handler)
  }, [])
  return { open, openTour, closeTour }
}

interface Rect { top: number; left: number; width: number; height: number }

export default function Tour({ open, onClose }: { open: boolean; onClose: () => void }) {
  const t = useT()
  const { lang } = useI18n()
  const { theme } = useTheme()
  const [i, setI] = useState(0)
  const [rect, setRect] = useState<Rect | null>(null)

  useEffect(() => { if (open) setI(0) }, [open])

  // Localiza o alvo do passo atual e mede sua posição (recalcula em resize).
  useLayoutEffect(() => {
    if (!open) return
    const measure = () => {
      const sel = STEPS[i]?.target
      const el = sel ? document.querySelector(sel) as HTMLElement | null : null
      if (el) {
        el.scrollIntoView({ block: 'nearest', inline: 'nearest' })
        const r = el.getBoundingClientRect()
        // elemento sem tamanho (ex.: nav escondido no mobile) → centraliza
        setRect(r.width > 0 && r.height > 0
          ? { top: r.top, left: r.left, width: r.width, height: r.height } : null)
      } else {
        setRect(null)
      }
    }
    measure()
    window.addEventListener('resize', measure)
    window.addEventListener('scroll', measure, true)
    return () => {
      window.removeEventListener('resize', measure)
      window.removeEventListener('scroll', measure, true)
    }
  }, [open, i])

  // Esc fecha; setas navegam.
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
  void lang

  // Recorte (spotlight) em volta do alvo, se houver.
  const hole = rect ? {
    top: rect.top - PAD, left: rect.left - PAD,
    width: rect.width + PAD * 2, height: rect.height + PAD * 2,
  } : null

  // Posição do balão: abaixo do alvo (ou acima se não couber); centralizado se sem alvo.
  let cardStyle: React.CSSProperties
  let placement: 'center' | 'below' | 'above' = 'center'
  if (hole) {
    const vw = window.innerWidth
    const belowTop = hole.top + hole.height + GAP
    const spaceBelow = window.innerHeight - belowTop
    placement = spaceBelow > 220 ? 'below' : 'above'
    let left = hole.left + hole.width / 2 - CARD_W / 2
    left = Math.max(12, Math.min(left, vw - CARD_W - 12))
    cardStyle = placement === 'below'
      ? { top: belowTop, left, width: CARD_W }
      : { bottom: window.innerHeight - hole.top + GAP, left, width: CARD_W }
  } else {
    cardStyle = { top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: CARD_W }
  }

  // Seta do balão apontando para o alvo.
  const arrowLeft = hole ? Math.max(16, Math.min(hole.left + hole.width / 2 - (cardStyle.left as number), CARD_W - 16)) : 0

  return (
    <div className="tour-root">
      {/* Camada escura com recorte; sem alvo, escurece tudo. */}
      {hole ? (
        <div className="tour-mask" style={{
          top: hole.top, left: hole.left, width: hole.width, height: hole.height,
        }} onClick={onClose} />
      ) : (
        <div className="tour-dim" onClick={onClose} />
      )}

      <div className={`tour-card tour-${placement}`} style={cardStyle}
           role="dialog" aria-modal="true" aria-label={t('tour.title')}>
        {placement !== 'center' && (
          <span className={`tour-arrow tour-arrow-${placement}`} style={{ left: arrowLeft }} />
        )}
        <button className="tour-close" aria-label={t('tour.skip')} onClick={onClose}><X size={17} /></button>

        <div className="tour-head">
          <span className="tour-icon"><Icon size={20} /></span>
          <h2 className="tour-title">{t(step.title, { name })}</h2>
        </div>
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
            {i > 0 && <button className="btn tour-btn-sm" onClick={() => setI(i - 1)}>{t('tour.back')}</button>}
            {isLast
              ? <button className="btn btn-primary tour-btn-sm" onClick={onClose}>{t('tour.done')}</button>
              : <button className="btn btn-primary tour-btn-sm" onClick={() => setI(i + 1)}>{t('tour.next')}</button>}
          </div>
        </div>
      </div>
    </div>
  )
}
