import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Database, BarChart3, Brain, Sparkles, ArrowRight } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { getCertifications } from '@/services/api'
import { useT } from '@/i18n'
import type { Certification } from '@/types'
import './Home.css'

const ICON: Record<string, LucideIcon> = {
  data_engineer: Database,
  data_analyst: BarChart3,
  machine_learning: Brain,
  data_scientist: Sparkles,
}

export default function Home() {
  const navigate = useNavigate()
  const t = useT()
  const { data, isLoading } = useQuery({ queryKey: ['certs'], queryFn: getCertifications })

  return (
    <div>
      <div className="home-hero">
        <h1>{t('home.heroTitle')}</h1>
        <p>
          {t('home.heroSub')}
          <br />
          {t('home.chooseTrack')}
        </p>
      </div>

      <div className="home-note" dangerouslySetInnerHTML={{ __html: t('home.note') }} />

      {isLoading && <div className="spinner" />}

      <div className="cert-grid">
        {data?.map((c: Certification) => {
          const Icon = ICON[c.type] ?? Brain
          return (
            <button key={c.id} className="cert-card" onClick={() => navigate(`/cert/${c.id}`)}>
              <div className="cert-card-top">
                <div className="cert-icon"><Icon size={22} /></div>
                <span className={`badge badge-${c.level}`}>{c.level}</span>
              </div>
              <h3>{c.name}</h3>
              <p className="muted">{c.description}</p>
              <div className="cert-card-foot">
                <span>{t('home.topics', { n: c.topics.length })}</span>
                <ArrowRight size={16} />
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
