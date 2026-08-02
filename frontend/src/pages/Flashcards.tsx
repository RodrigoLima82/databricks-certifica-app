import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react'
import { getFlashcards } from '@/services/api'
import { useT } from '@/i18n'
import type { Certification } from '@/types'
import './Flashcards.css'

export default function Flashcards({ cert }: { cert: Certification }) {
  const t = useT()
  const { data, isLoading } = useQuery({
    queryKey: ['flashcards', cert.id],
    queryFn: () => getFlashcards(cert.id),
  })
  const [topic, setTopic] = useState<string>('all')
  const [idx, setIdx] = useState(0)
  const [flipped, setFlipped] = useState(false)

  const cards = useMemo(() => {
    const all = data ?? []
    return topic === 'all' ? all : all.filter(c => c.topic === topic)
  }, [data, topic])

  if (isLoading) return <div className="spinner" />
  if (!data || data.length === 0)
    return <p className="muted fc-empty">{t('flashcards.empty')}</p>

  const card = cards[idx]
  const go = (d: number) => { setFlipped(false); setIdx(i => (i + d + cards.length) % cards.length) }

  return (
    <div className="fc">
      <div className="fc-filter">
        <button className={topic === 'all' ? 'on' : ''} onClick={() => { setTopic('all'); setIdx(0); setFlipped(false) }}>{t('flashcards.all')}</button>
        {cert.topics.map(tp => (
          <button key={tp} className={topic === tp ? 'on' : ''}
            onClick={() => { setTopic(tp); setIdx(0); setFlipped(false) }}>{tp}</button>
        ))}
      </div>

      {card ? (
        <>
          <div className="fc-counter">{idx + 1} / {cards.length} · {card.topic}</div>
          <div className={`fc-card ${flipped ? 'flipped' : ''}`} onClick={() => setFlipped(f => !f)}>
            <div className="fc-inner">
              <div className="fc-front"><span className="fc-hint">{t('flashcards.question')}</span><p>{card.front}</p></div>
              <div className="fc-back"><span className="fc-hint">{t('flashcards.answer')}</span><p>{card.back}</p></div>
            </div>
          </div>
          <div className="fc-nav">
            <button className="btn" onClick={() => go(-1)}><ChevronLeft size={16} /> {t('flashcards.previous')}</button>
            <button className="btn" onClick={() => setFlipped(f => !f)}><RefreshCw size={15} /> {t('flashcards.flip')}</button>
            <button className="btn" onClick={() => go(1)}>{t('flashcards.next')} <ChevronRight size={16} /></button>
          </div>
        </>
      ) : <p className="muted fc-empty">{t('flashcards.noneTopic')}</p>}
    </div>
  )
}
