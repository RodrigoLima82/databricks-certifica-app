import { useState } from 'react'
import {
  GraduationCap, ListTodo, Loader2, ExternalLink, Code2, AlertTriangle,
  Lightbulb, Wrench, ChevronDown, ChevronRight, BookOpen,
} from 'lucide-react'
import { deepDive, handsOnChecklist } from '@/services/api'
import type { DeepDiveResponse, HandsOnTask } from '@/services/api'
import { useT } from '@/i18n'
import type { Certification } from '@/types'
import './StudyAI.css'

/**
 * "Estudiar con IA" — implementa dos pasos del AI Prep Guide de Databricks:
 *  - Deep dive (Step 4.3): enseñar un objetivo con fuentes oficiales.
 *  - Hands-on checklist (Step 5, CRÍTICO): tareas prácticas por certificación.
 */
export default function StudyAI({ cert }: { cert: Certification }) {
  const t = useT()

  // deep dive
  const [objective, setObjective] = useState<string>(cert.topics[0] ?? '')
  const [dd, setDd] = useState<DeepDiveResponse | null>(null)
  const [ddLoading, setDdLoading] = useState(false)
  const [ddError, setDdError] = useState<string | null>(null)

  // hands-on
  const [tasks, setTasks] = useState<HandsOnTask[] | null>(null)
  const [hoLoading, setHoLoading] = useState(false)
  const [hoError, setHoError] = useState<string | null>(null)
  const [done, setDone] = useState<Record<number, boolean>>({})
  const [openHow, setOpenHow] = useState<Record<number, boolean>>({})

  async function runDeepDive(obj: string) {
    setObjective(obj); setDdLoading(true); setDdError(null); setDd(null)
    try {
      const r = await deepDive(cert.id, obj)
      if (!r.success) throw new Error(r.message || 'error')
      setDd(r)
    } catch (e: any) {
      setDdError(e?.response?.data?.detail || e?.message || 'Error')
    } finally { setDdLoading(false) }
  }

  async function runHandsOn() {
    setHoLoading(true); setHoError(null)
    try {
      const r = await handsOnChecklist(cert.id)
      if (!r.success) throw new Error(r.message || 'error')
      setTasks(r.tasks)
    } catch (e: any) {
      setHoError(e?.response?.data?.detail || e?.message || 'Error')
    } finally { setHoLoading(false) }
  }

  return (
    <div className="sa">
      {/* Deep dive */}
      <div className="card sa-block">
        <h3><GraduationCap size={18} /> {t('study.deepDiveTitle')}</h3>
        <p className="sa-sub">{t('study.deepDiveSub')}</p>
        <div className="sa-topics">
          {cert.topics.map(tp => (
            <button
              key={tp}
              className={`sa-chip ${objective === tp ? 'active' : ''}`}
              onClick={() => runDeepDive(tp)}
              disabled={ddLoading}
            >{tp}</button>
          ))}
        </div>

        {ddLoading && <div className="sa-loading"><Loader2 size={18} className="spinning" /> {t('study.thinking')}</div>}
        {ddError && <div className="sa-error">{ddError}</div>}

        {dd && !ddLoading && (
          <div className="sa-dd">
            <h4>{dd.objective}</h4>
            <div className="sa-dd-block"><Lightbulb size={15} /><div><b>{t('study.coreConcept')}</b><p>{dd.core_concept}</p></div></div>
            <div className="sa-dd-block"><GraduationCap size={15} /><div><b>{t('study.howItWorks')}</b><p>{dd.how_it_works}</p></div></div>
            <div className="sa-dd-block"><Wrench size={15} /><div><b>{t('study.whenToUse')}</b><p>{dd.when_to_use}</p></div></div>
            <div className="sa-dd-block"><AlertTriangle size={15} /><div><b>{t('study.commonMistakes')}</b><p>{dd.common_mistakes}</p></div></div>
            {dd.code_example && (
              <div className="sa-dd-block"><Code2 size={15} /><div style={{ flex: 1 }}><b>{t('study.codeExample')}</b>
                <pre className="sa-code">{dd.code_example}</pre></div></div>
            )}
            {dd.doc_url && (
              <a href={dd.doc_url} target="_blank" rel="noreferrer" className="btn sa-doc">
                <ExternalLink size={15} /> {t('study.officialDocs')}
              </a>
            )}
          </div>
        )}
      </div>

      {/* Hands-on checklist */}
      <div className="card sa-block">
        <h3><ListTodo size={18} /> {t('study.handsOnTitle')}</h3>
        <p className="sa-sub">{t('study.handsOnSub')}</p>
        {!tasks && (
          <button className="btn btn-primary" onClick={runHandsOn} disabled={hoLoading}>
            {hoLoading ? <Loader2 size={16} className="spinning" /> : <ListTodo size={16} />} {t('study.generateChecklist')}
          </button>
        )}
        {hoError && <div className="sa-error">{hoError}</div>}
        {tasks && (
          <>
            <div className="sa-progress">{Object.values(done).filter(Boolean).length}/{tasks.length} {t('study.completed')}</div>
            <ul className="sa-tasks">
              {tasks.map((tk, i) => (
                <li key={i} className={done[i] ? 'sa-task done' : 'sa-task'}>
                  <label>
                    <input type="checkbox" checked={!!done[i]} onChange={e => setDone(d => ({ ...d, [i]: e.target.checked }))} />
                    <div>
                      <span className="sa-task-text">{tk.task}</span>
                      <span className="sa-task-meta">
                        {tk.objective && <span className="sa-task-obj">{tk.objective}</span>}
                        {tk.est_minutes ? <span className="sa-task-min">~{tk.est_minutes} min</span> : null}
                      </span>
                    </div>
                  </label>

                  {((tk.steps && tk.steps.length > 0) || tk.doc_url) && (
                    <div className="sa-how">
                      {tk.steps && tk.steps.length > 0 && (
                        <button type="button" className="sa-how-toggle"
                          onClick={() => setOpenHow(o => ({ ...o, [i]: !o[i] }))}>
                          {openHow[i] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                          {t('study.howTo')}
                        </button>
                      )}
                      {openHow[i] && tk.steps && (
                        <ol className="sa-how-steps">
                          {tk.steps.map((s, si) => <li key={si}>{s}</li>)}
                        </ol>
                      )}
                      {tk.doc_url && (
                        <a className="sa-how-doc" href={tk.doc_url} target="_blank" rel="noreferrer">
                          <BookOpen size={13} /> {t('study.officialDoc')} <ExternalLink size={11} />
                        </a>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
            <button className="btn sa-regen" onClick={runHandsOn} disabled={hoLoading}>
              {hoLoading ? <Loader2 size={14} className="spinning" /> : null} {t('study.regenerate')}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
