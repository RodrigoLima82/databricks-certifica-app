import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Target, TrendingUp, TrendingDown, Minus, CheckCircle2, ExternalLink,
  Loader2, Sparkles, PlayCircle, Award,
} from 'lucide-react'
import { getStudyPlan, topicQuiz, submitTest } from '@/services/api'
import { useT } from '@/i18n'
import type { Certification, StudyPlanTopic, Question, AnswerSubmission, TestSession } from '@/types'
import './StudyPlan.css'

const STATUS_COLOR: Record<string, string> = {
  weak: '#dc2626', improving: '#d97706', mastered: '#16a34a',
}

export default function StudyPlan({ cert }: { cert: Certification }) {
  const t = useT()
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['study-plan', cert.id],
    queryFn: () => getStudyPlan(cert.id),
  })

  // mini-teste focado por tópico
  const [quizTopic, setQuizTopic] = useState<string | null>(null)
  const [quizSession, setQuizSession] = useState<TestSession | null>(null)
  const [quizQs, setQuizQs] = useState<Question[]>([])
  const [quizAns, setQuizAns] = useState<Record<string, number[]>>({})
  const [quizLoading, setQuizLoading] = useState(false)
  const [quizScore, setQuizScore] = useState<number | null>(null)
  const [quizErr, setQuizErr] = useState<string | null>(null)

  async function startTopicQuiz(topic: string) {
    setQuizErr(null); setQuizLoading(true); setQuizTopic(topic)
    setQuizSession(null); setQuizQs([]); setQuizAns({}); setQuizScore(null)
    try {
      const s = await topicQuiz(cert.id, topic, 6)
      if (!s.questions?.length) throw new Error('no questions')
      setQuizSession(s); setQuizQs(s.questions)
    } catch (e: any) {
      setQuizErr(e?.response?.data?.detail ?? e?.message ?? t('plan.quizError'))
      setQuizTopic(null)
    } finally { setQuizLoading(false) }
  }

  function pick(qid: string, optIdx: number, multi: boolean) {
    setQuizAns(prev => {
      const cur = prev[qid] ?? []
      if (multi) return { ...prev, [qid]: cur.includes(optIdx) ? cur.filter(i => i !== optIdx) : [...cur, optIdx] }
      return { ...prev, [qid]: [optIdx] }
    })
  }

  async function submitTopicQuiz() {
    if (!quizSession) return
    setQuizLoading(true); setQuizErr(null)
    try {
      const answers: AnswerSubmission[] = quizSession.questions.map(q => ({
        question_id: q.id, selected: quizAns[q.id] ?? [],
      }))
      const res = await submitTest({
        session_id: quizSession.id, certification_id: cert.id, answers,
      })
      setQuizScore(res.score_pct)
      refetch()   // atualiza o mastery com a nova tentativa
    } catch (e: any) {
      setQuizErr(e?.response?.data?.detail ?? t('plan.quizError'))
    } finally { setQuizLoading(false) }
  }

  function closeQuiz() {
    setQuizTopic(null); setQuizSession(null); setQuizQs([]); setQuizAns({}); setQuizScore(null); setQuizErr(null)
  }

  if (isLoading) return <div className="spinner" />
  if (!data) return <p className="muted">{t('plan.error')}</p>

  if (!data.topics.length) {
    return (
      <div className="card sp-empty">
        <Target size={30} color="var(--brand-primary)" />
        <h3>{t('plan.title')}</h3>
        <p className="muted">{data.message || t('plan.empty')}</p>
      </div>
    )
  }

  const weak = data.topics.filter(x => x.status !== 'mastered')
  const mastered = data.topics.filter(x => x.status === 'mastered')

  const TrendIcon = ({ tp }: { tp: StudyPlanTopic }) =>
    tp.trend === 'up' ? <TrendingUp size={14} color="#16a34a" />
      : tp.trend === 'down' ? <TrendingDown size={14} color="#dc2626" />
        : <Minus size={14} color="#9ca3af" />

  return (
    <div className="sp">
      <div className="sp-head card">
        <div>
          <h3><Target size={19} color="var(--brand-primary)" /> {t('plan.title')}</h3>
          <p className="muted">{t('plan.subtitle', { mark: data.mastery_mark })}</p>
        </div>
        <div className="sp-head-stats">
          <div><b>{data.attempts_count}</b><span>{t('plan.attempts')}</span></div>
          <div><b style={{ color: STATUS_COLOR.mastered }}>{mastered.length}</b><span>{t('plan.mastered')}</span></div>
          <div><b style={{ color: STATUS_COLOR.weak }}>{weak.length}</b><span>{t('plan.toImprove')}</span></div>
        </div>
      </div>

      {weak.length > 0 && <h4 className="sp-section">{t('plan.focusHere')}</h4>}
      {weak.map(tp => (
        <div key={tp.topic} className="card sp-topic">
          <div className="sp-topic-head">
            <span className="sp-badge" style={{ background: STATUS_COLOR[tp.status] }}>
              {t(`plan.status.${tp.status}`)}
            </span>
            <span className="sp-topic-name">{tp.topic}</span>
            <span className="sp-topic-pct" style={{ color: STATUS_COLOR[tp.status] }}>
              {tp.pct}% <TrendIcon tp={tp} />
            </span>
          </div>
          <div className="sp-bar"><div style={{ width: `${tp.pct}%`, background: STATUS_COLOR[tp.status] }} /></div>
          <div className="sp-topic-meta muted">
            {t('plan.correctOf', { c: tp.correct, tt: tp.total })} · {t('plan.acrossAttempts', { n: tp.attempts })}
          </div>

          {tp.classes.length > 0 && (
            <div className="sp-classes">
              <span className="sp-classes-lbl">{t('plan.studyThese')}</span>
              {tp.classes.map(c => (
                <a key={c.id} className="sp-class" href={c.url || '#'} target="_blank" rel="noreferrer">
                  <ExternalLink size={13} />
                  <span>{c.title}</span>
                  {c.duration && <em>{c.duration}</em>}
                </a>
              ))}
            </div>
          )}

          <button className="btn btn-outline sp-quiz-btn" onClick={() => startTopicQuiz(tp.topic)}
            disabled={quizLoading && quizTopic === tp.topic}>
            {quizLoading && quizTopic === tp.topic
              ? <><Loader2 size={15} className="spinning" /> {t('plan.generating')}</>
              : <><PlayCircle size={15} /> {t('plan.practiceTopic')}</>}
          </button>
        </div>
      ))}

      {mastered.length > 0 && (
        <>
          <h4 className="sp-section"><Award size={16} color={STATUS_COLOR.mastered} /> {t('plan.masteredTitle')}</h4>
          <div className="card sp-mastered">
            {mastered.map(tp => (
              <div key={tp.topic} className="sp-mastered-row">
                <CheckCircle2 size={15} color={STATUS_COLOR.mastered} />
                <span>{tp.topic}</span><b>{tp.pct}%</b>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Mini-teste focado (overlay simples inline) */}
      {quizTopic && (
        <div className="sp-quiz-overlay" onClick={e => { if (e.target === e.currentTarget) closeQuiz() }}>
          <div className="card sp-quiz card-scroll">
            <div className="sp-quiz-top">
              <b><Sparkles size={15} color="var(--brand-primary)" /> {t('plan.miniQuiz')}: {quizTopic}</b>
              <button className="link-btn" onClick={closeQuiz}>✕</button>
            </div>

            {quizErr && <div className="sp-quiz-err">{quizErr}</div>}

            {quizScore === null ? (
              <>
                {quizQs.map((q, i) => {
                  const multi = q.question_type === 'multiple_select'
                  const sel = quizAns[q.id] ?? []
                  return (
                    <div key={q.id} className="sp-q">
                      <p className="sp-q-text">{i + 1}. {q.question_text}</p>
                      {q.options.map((o, oi) => (
                        <label key={oi} className={`sp-opt ${sel.includes(oi) ? 'on' : ''}`}>
                          <input type={multi ? 'checkbox' : 'radio'} name={q.id}
                            checked={sel.includes(oi)} onChange={() => pick(q.id, oi, multi)} />
                          <span>{o}</span>
                        </label>
                      ))}
                    </div>
                  )
                })}
                <button className="btn btn-primary sp-quiz-submit" onClick={submitTopicQuiz}
                  disabled={quizLoading || Object.keys(quizAns).length < quizQs.length}>
                  {quizLoading ? <><Loader2 size={15} className="spinning" /> {t('plan.grading')}</> : t('plan.submitQuiz')}
                </button>
              </>
            ) : (
              <div className="sp-quiz-result">
                <div className="sp-quiz-score" style={{ color: quizScore >= data.mastery_mark ? STATUS_COLOR.mastered : STATUS_COLOR.improving }}>
                  {quizScore}%
                </div>
                <p>{quizScore >= data.mastery_mark ? t('plan.quizPass', { mark: data.mastery_mark }) : t('plan.quizKeep', { mark: data.mastery_mark })}</p>
                <button className="btn btn-outline" onClick={closeQuiz}>{t('plan.close')}</button>
              </div>
            )}
          </div>
        </div>
      )}

      {isFetching && <div className="sp-refetch muted"><Loader2 size={13} className="spinning" /> {t('plan.updating')}</div>}
    </div>
  )
}
