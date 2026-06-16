import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Database, BarChart3, Brain, Sparkles, ArrowRight } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { getCertifications } from '@/services/api'
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
  const { data, isLoading } = useQuery({ queryKey: ['certs'], queryFn: getCertifications })

  return (
    <div>
      <div className="home-hero">
        <h1>Prepare-se para as certificações Databricks</h1>
        <p>
          Simulados com correção, explicações detalhadas, flashcards e geração de questões via IA.
          <br />
          Escolha sua trilha e comece a praticar.
        </p>
      </div>

      <div className="home-note">
        <b>Nota:</b> Estes simulados não refletem o mesmo nível de rigor dos exames de
        certificação Databricks. Os exames oficiais focam em questões baseadas em aplicação,
        enquanto estes são mais voltados à memorização. Estas questões ajudam na preparação,
        mas é recomendável fazer o eLearning e os labs.
      </div>

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
                <span>{c.topics.length} tópicos</span>
                <ArrowRight size={16} />
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
