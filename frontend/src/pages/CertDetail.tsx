import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, FlaskConical, Layers, ExternalLink } from 'lucide-react'
import { getCertification } from '@/services/api'
import PracticeTest from '@/pages/PracticeTest'
import Flashcards from '@/pages/Flashcards'
import './CertDetail.css'

type Tab = 'overview' | 'practice' | 'flashcards'

export default function CertDetail() {
  const { id = '' } = useParams()
  const [tab, setTab] = useState<Tab>('overview')
  const { data: cert, isLoading } = useQuery({
    queryKey: ['cert', id],
    queryFn: () => getCertification(id),
  })

  if (isLoading) return <div className="spinner" />
  if (!cert) return <p className="muted">Certificação não encontrada.</p>

  return (
    <div>
      <div className="cd-header card">
        <div className="cd-header-main">
          <span className={`badge badge-${cert.level}`}>{cert.level}</span>
          <h1>{cert.name}</h1>
          <p className="muted">{cert.description}</p>
          <div className="cd-links">
            {cert.exam_guide_url && (
              <a href={cert.exam_guide_url} target="_blank" rel="noreferrer" className="btn">
                <BookOpen size={16} /> Guia do Exame
              </a>
            )}
          </div>
        </div>
      </div>

      <div className="cd-tabs">
        <button className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}>
          <Layers size={16} /> Visão geral
        </button>
        <button className={tab === 'practice' ? 'active' : ''} onClick={() => setTab('practice')}>
          <FlaskConical size={16} /> Simulado
        </button>
        <button className={tab === 'flashcards' ? 'active' : ''} onClick={() => setTab('flashcards')}>
          <BookOpen size={16} /> Flashcards
        </button>
      </div>

      <div className="cd-panel">
        {tab === 'overview' && (
          <div className="cd-overview">
            <div className="card cd-topics">
              <h3>Tópicos cobertos</h3>
              <ul>{cert.topics.map(t => <li key={t}>{t}</li>)}</ul>
            </div>
            <div className="cd-overview-cards">
              <div className="card cd-action" onClick={() => setTab('practice')}>
                <FlaskConical size={26} color="#FF3621" />
                <h4>Simulado</h4>
                <p className="muted">Monte um teste de 5 a 60 questões, com correção e explicações.</p>
              </div>
              <div className="card cd-action" onClick={() => setTab('flashcards')}>
                <BookOpen size={26} color="#FF3621" />
                <h4>Flashcards</h4>
                <p className="muted">Revise conceitos-chave de forma rápida e interativa.</p>
              </div>
            </div>
            {cert.resources?.length > 0 && (
              <div className="card cd-resources">
                <h3>Recursos de estudo</h3>
                <ul>
                  {cert.resources.map(r => (
                    <li key={r.url}>
                      <a href={r.url} target="_blank" rel="noreferrer">
                        <ExternalLink size={14} /> {r.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        {tab === 'practice' && <PracticeTest cert={cert} />}
        {tab === 'flashcards' && <Flashcards cert={cert} />}
      </div>
    </div>
  )
}
