import { useEffect, useMemo, useState } from 'react'
import {
  Sparkles, Clock, CheckCircle2, XCircle, RotateCcw, ListChecks, Loader2,
  Wrench, GraduationCap,
} from 'lucide-react'
import { createTest, createMockExam, submitTest, repairAnswers } from '@/services/api'
import type { RepairItem, WrongAnswerIn } from '@/services/api'
import { useT } from '@/i18n'
import type {
  Certification, TestSession, TestResult, AnswerSubmission,
} from '@/types'
import './PracticeTest.css'

type Phase = 'setup' | 'running' | 'results' | 'review'

export default function PracticeTest({ cert }: { cert: Certification }) {
  const t = useT()
  const [phase, setPhase] = useState<Phase>('setup')

  // setup state
  const [selTopics, setSelTopics] = useState<string[]>(cert.topics)
  const [numQ, setNumQ] = useState(20)
  const [aiGen, setAiGen] = useState(false)
  const [aiCount, setAiCount] = useState(5)
  const [loading, setLoading] = useState(false)
  const [mockLoading, setMockLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // running state
  const [session, setSession] = useState<TestSession | null>(null)
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<string, number[]>>({})
  const [startedAt, setStartedAt] = useState(0)
  const [elapsed, setElapsed] = useState(0)

  // results
  const [result, setResult] = useState<TestResult | null>(null)

  // repair (AI Prep Guide, Step 4.5)
  const [repairItems, setRepairItems] = useState<RepairItem[] | null>(null)
  const [repairLoading, setRepairLoading] = useState(false)
  const [repairError, setRepairError] = useState<string | null>(null)

  async function runRepair() {
    if (!session) return
    setRepairLoading(true); setRepairError(null)
    const wrong: WrongAnswerIn[] = session.questions
      .filter(q => sorted(answers[q.id] ?? []).join(',') !== sorted(q.correct_answers).join(','))
      .map(q => ({
        question_text: q.question_text, options: q.options,
        correct_answers: q.correct_answers, selected: answers[q.id] ?? [],
        topic: q.topic, explanation: q.explanation,
      }))
    if (!wrong.length) { setRepairItems([]); setRepairLoading(false); return }
    try {
      const r = await repairAnswers(cert.id, wrong)
      if (!r.success) throw new Error(r.message || 'error')
      setRepairItems(r.items)
    } catch (e: any) {
      setRepairError(e?.response?.data?.detail || e?.message || 'Error')
    } finally {
      setRepairLoading(false)
    }
  }

  useEffect(() => {
    if (phase !== 'running') return
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000)
    return () => clearInterval(t)
  }, [phase, startedAt])

  const toggleTopic = (t: string) =>
    setSelTopics(s => s.includes(t) ? s.filter(x => x !== t) : [...s, t])

  async function start() {
    setError(null); setLoading(true)
    try {
      const s = await createTest({
        certification_id: cert.id,
        num_questions: numQ,
        topics: selTopics.length ? selTopics : undefined,
        ai_generate: aiGen,
        ai_count: aiGen ? aiCount : 0,
      })
      setSession(s); setIdx(0); setAnswers({})
      setStartedAt(Date.now()); setElapsed(0); setPhase('running')
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? t('practice.createError'))
    } finally { setLoading(false) }
  }

  // Step 4.4 — simulacro completo (nº real de preguntas + distribución por dominio)
  async function startMock() {
    setError(null); setMockLoading(true)
    try {
      const s = await createMockExam(cert.id)
      setSession(s); setIdx(0); setAnswers({})
      setStartedAt(Date.now()); setElapsed(0); setPhase('running')
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? t('practice.mockError'))
    } finally { setMockLoading(false) }
  }

  function pick(qid: string, optIdx: number, multi: boolean) {
    setAnswers(prev => {
      const cur = prev[qid] ?? []
      if (multi) {
        return { ...prev, [qid]: cur.includes(optIdx) ? cur.filter(i => i !== optIdx) : [...cur, optIdx] }
      }
      return { ...prev, [qid]: [optIdx] }
    })
  }

  async function finish() {
    if (!session) return
    setLoading(true)
    try {
      const payload: AnswerSubmission[] = session.questions.map(q => ({
        question_id: q.id, selected: answers[q.id] ?? [],
      }))
      const r = await submitTest({
        session_id: session.id, certification_id: cert.id,
        answers: payload, duration_sec: elapsed,
      })
      setResult(r); setPhase('results')
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? t('practice.gradeError'))
    } finally { setLoading(false) }
  }

  function reset() {
    setPhase('setup'); setSession(null); setResult(null); setAnswers({})
    setRepairItems(null); setRepairError(null)
  }

  const answeredCount = useMemo(
    () => session ? session.questions.filter(q => (answers[q.id]?.length ?? 0) > 0).length : 0,
    [session, answers],
  )
  const fmtTime = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

  // ── SETUP ──────────────────────────────────────────────────────────────────
  if (phase === 'setup') {
    return (
      <div className="pt-setup">
        <div className="card pt-setup-card">
          <h3>{t('practice.configTitle')}</h3>
          <p className="muted">{t('practice.personalize')}</p>

          <label className="pt-field-label">{t('practice.topics')}</label>
          <div className="pt-topics">
            {cert.topics.map(t => (
              <button key={t}
                className={`pt-topic ${selTopics.includes(t) ? 'on' : ''}`}
                onClick={() => toggleTopic(t)}>{t}</button>
            ))}
          </div>
          <div className="pt-topics-actions">
            <button className="link-btn" onClick={() => setSelTopics(cert.topics)}>{t('practice.selectAll')}</button>
            <button className="link-btn" onClick={() => setSelTopics([])}>{t('practice.clear')}</button>
          </div>

          <label className="pt-field-label">{t('practice.numQuestions')} <b>{numQ}</b></label>
          <input type="range" min={5} max={60} step={5} value={numQ}
            onChange={e => setNumQ(Number(e.target.value))} className="pt-range" />
          <div className="pt-range-marks"><span>5</span><span>60</span></div>

          <label className="pt-ai">
            <input type="checkbox" checked={aiGen} onChange={e => setAiGen(e.target.checked)} />
            <Sparkles size={15} color="#6a1b9a" />
            <span>{t('practice.genAI')}</span>
          </label>
          {aiGen && (
            <div className="pt-ai-count">
              {t('practice.howMany')} <b>{aiCount}</b>
              <input type="range" min={1} max={10} value={aiCount}
                onChange={e => setAiCount(Number(e.target.value))} className="pt-range" />
            </div>
          )}

          {error && <div className="pt-error">{error}</div>}
          <button className="btn btn-primary btn-lg pt-start"
            disabled={loading || mockLoading || selTopics.length === 0} onClick={start}>
            {loading ? <><Loader2 size={18} className="spinning" /> {t('practice.creating')}</> : t('practice.start')}
          </button>

          {/* Step 4.4 — simulacro completo estilo examen real */}
          <div className="pt-mock">
            <div className="pt-mock-head">
              <GraduationCap size={18} color="#EC0000" />
              <div>
                <b>{t('practice.mockTitle')}</b>
                <p className="muted">{t('practice.mockDesc')}</p>
              </div>
            </div>
            <button className="btn btn-outline pt-mock-btn"
              disabled={loading || mockLoading} onClick={startMock}>
              {mockLoading
                ? <><Loader2 size={16} className="spinning" /> {t('practice.mockCreating')}</>
                : <><Sparkles size={15} /> {t('practice.mockStart')}</>}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── RUNNING ─────────────────────────────────────────────────────────────────
  if (phase === 'running' && session) {
    const q = session.questions[idx]
    const multi = q.question_type === 'multiple_select'
    const sel = answers[q.id] ?? []
    return (
      <div className="pt-run">
        {session.is_mock && (
          <div className="pt-mock-banner">
            <GraduationCap size={15} /> {t('practice.mockRunning', { n: session.questions.length })}
          </div>
        )}
        <div className="pt-run-bar">
          <span><Clock size={15} /> {fmtTime(elapsed)}</span>
          <span>{t('practice.questionOf', { i: idx + 1, n: session.questions.length })}</span>
          <span>{t('practice.answered', { n: answeredCount })}</span>
        </div>
        <div className="pt-progress"><div style={{ width: `${(answeredCount / session.questions.length) * 100}%` }} /></div>

        <div className="card pt-question">
          <div className="pt-q-meta">
            <span className="pt-topic-tag">{q.topic}</span>
            {q.is_ai_generated && <span className="badge badge-ai">IA</span>}
            <span className="pt-diff">{t('practice.difficulty', { d: q.difficulty })}</span>
          </div>
          <h3 className="pt-q-text">{q.question_text}</h3>
          {multi && <p className="pt-multi-hint">{t('practice.selectAllHint')}</p>}
          <div className="pt-options">
            {q.options.map((opt, i) => (
              <button key={i}
                className={`pt-option ${sel.includes(i) ? 'sel' : ''}`}
                onClick={() => pick(q.id, i, multi)}>
                <span className={`pt-mark ${multi ? 'sq' : ''}`}>{sel.includes(i) ? '✓' : ''}</span>
                <span>{opt}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="pt-nav">
          <button className="btn" disabled={idx === 0} onClick={() => setIdx(i => i - 1)}>{t('practice.previous')}</button>
          {idx < session.questions.length - 1
            ? <button className="btn btn-primary" onClick={() => setIdx(i => i + 1)}>{t('practice.next')}</button>
            : <button className="btn btn-primary" disabled={loading} onClick={finish}>
                {loading ? <><Loader2 size={16} className="spinning" /> {t('practice.grading')}</> : t('practice.finish')}
              </button>}
        </div>
        <button className="link-btn pt-end-early" onClick={finish}>{t('practice.endNow')}</button>
      </div>
    )
  }

  // ── RESULTS ─────────────────────────────────────────────────────────────────
  if (phase === 'results' && result) {
    const pass = result.passed
    return (
      <div className="pt-results">
        <div className="card pt-score-card">
          <div className="pt-emoji">{pass ? '🎉' : '📚'}</div>
          <div className={`pt-score ${pass ? 'pass' : 'fail'}`}>{result.score_pct}%</div>
          <div className={`pt-verdict-badge ${pass ? 'ok' : 'no'}`}>
            {pass ? t('practice.approved') : t('practice.reproved')} · {t('practice.cut', { m: result.pass_mark })}
          </div>
          <p>{t('practice.correctOf', { c: result.correct, t: result.total })}</p>
          <div className="pt-stats">
            <div><b>{result.correct}</b><span>{t('practice.correct')}</span></div>
            <div><b>{result.total - result.correct}</b><span>{t('practice.incorrect')}</span></div>
            <div><b>{fmtTime(result.duration_sec ?? 0)}</b><span>{t('practice.time')}</span></div>
            {result.repeated_questions > 0 &&
              <div><b>{result.repeated_questions}</b><span>{t('practice.repeated')}</span></div>}
          </div>
        </div>

        <div className="card pt-topic-breakdown">
          <h3>{t('practice.perfByTopic')}</h3>
          {result.by_topic.map(t => {
            const pct = Math.round((t.correct / t.total) * 100)
            return (
              <div key={t.topic} className="pt-topic-row">
                <span>{t.topic}</span>
                <div className="pt-topic-bar"><div style={{ width: `${pct}%` }} className={pct >= 70 ? 'ok' : 'low'} /></div>
                <span className="pt-topic-pct">{t.correct}/{t.total}</span>
              </div>
            )
          })}
        </div>

        <div className="pt-results-actions">
          <button className="btn" onClick={() => setPhase('review')}><ListChecks size={16} /> {t('practice.reviewAnswers')}</button>
          {result.correct < result.total && (
            <button className="btn" onClick={runRepair} disabled={repairLoading}>
              {repairLoading ? <Loader2 size={16} className="spinning" /> : <Wrench size={16} />} {t('practice.explainMistakes')}
            </button>
          )}
          <button className="btn btn-primary" onClick={reset}><RotateCcw size={16} /> {t('practice.newTest')}</button>
        </div>

        {repairError && <div className="card pt-repair-error">{repairError}</div>}

        {repairItems && repairItems.length > 0 && (
          <div className="card pt-repair">
            <h3><Wrench size={17} /> {t('practice.repairTitle')}</h3>
            <p className="pt-repair-sub">{t('practice.repairSub')}</p>
            {repairItems.map((it, i) => (
              <div key={i} className="pt-repair-item">
                <p className="pt-repair-q"><b>{i + 1}.</b> {it.question_text}</p>
                <div className="pt-repair-block pt-repair-mis">
                  <span className="pt-repair-lbl">{t('practice.misconception')}</span> {it.misconception}
                </div>
                <div className="pt-repair-block pt-repair-why">
                  <span className="pt-repair-lbl">{t('practice.whyCorrect')}</span> {it.why_correct}
                </div>
                <div className="pt-repair-block pt-repair-rel">
                  <span className="pt-repair-lbl">{t('practice.relatedQuestion')}</span> {it.related_question}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // ── REVIEW ──────────────────────────────────────────────────────────────────
  if (phase === 'review' && session && result) {
    return (
      <div className="pt-review">
        <div className="pt-review-head">
          <h3>{t('practice.reviewTitle', { c: result.correct, t: result.total })}</h3>
          <button className="btn" onClick={() => setPhase('results')}>{t('practice.backToResult')}</button>
        </div>
        {session.questions.map((q, i) => {
          const sel = answers[q.id] ?? []
          const correct = sorted(sel).join(',') === sorted(q.correct_answers).join(',')
          return (
            <div key={q.id} className="card pt-rev-q">
              <div className="pt-rev-top">
                <span className="pt-topic-tag">{q.topic}</span>
                {q.is_ai_generated && <span className="badge badge-ai">IA</span>}
                <span className={`pt-verdict ${correct ? 'ok' : 'no'}`}>
                  {correct ? <><CheckCircle2 size={15} /> {t('practice.correctLabel')}</> : <><XCircle size={15} /> {t('practice.incorrectLabel')}</>}
                </span>
              </div>
              <p className="pt-rev-qtext"><b>{i + 1}.</b> {q.question_text}</p>
              <div className="pt-rev-opts">
                {q.options.map((opt, oi) => {
                  const isCorrect = q.correct_answers.includes(oi)
                  const isSel = sel.includes(oi)
                  return (
                    <div key={oi} className={`pt-rev-opt ${isCorrect ? 'correct' : ''} ${isSel && !isCorrect ? 'wrong' : ''}`}>
                      <span>{opt}</span>
                      {isCorrect && <span className="pt-tag ok">{t('practice.correctTag')}</span>}
                      {isSel && !isCorrect && <span className="pt-tag no">{t('practice.yourAnswerWrong')}</span>}
                    </div>
                  )
                })}
              </div>
              {q.explanation && <div className="pt-explain"><b>{t('practice.explanation')}</b> {q.explanation}</div>}
            </div>
          )
        })}
      </div>
    )
  }

  return null
}

function sorted(a: number[]) { return [...a].sort((x, y) => x - y) }
