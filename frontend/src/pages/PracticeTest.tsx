import { useEffect, useMemo, useState } from 'react'
import {
  Sparkles, Clock, CheckCircle2, XCircle, RotateCcw, ListChecks, Loader2,
} from 'lucide-react'
import { createTest, submitTest } from '@/services/api'
import type {
  Certification, TestSession, TestResult, AnswerSubmission,
} from '@/types'
import './PracticeTest.css'

type Phase = 'setup' | 'running' | 'results' | 'review'

export default function PracticeTest({ cert }: { cert: Certification }) {
  const [phase, setPhase] = useState<Phase>('setup')

  // setup state
  const [selTopics, setSelTopics] = useState<string[]>(cert.topics)
  const [numQ, setNumQ] = useState(20)
  const [aiGen, setAiGen] = useState(false)
  const [aiCount, setAiCount] = useState(5)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // running state
  const [session, setSession] = useState<TestSession | null>(null)
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<string, number[]>>({})
  const [startedAt, setStartedAt] = useState(0)
  const [elapsed, setElapsed] = useState(0)

  // results
  const [result, setResult] = useState<TestResult | null>(null)

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
      setError(e?.response?.data?.detail ?? 'Falha ao criar o simulado.')
    } finally { setLoading(false) }
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
      setError(e?.response?.data?.detail ?? 'Falha ao corrigir o simulado.')
    } finally { setLoading(false) }
  }

  function reset() {
    setPhase('setup'); setSession(null); setResult(null); setAnswers({})
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
          <h3>Configurar simulado</h3>
          <p className="muted">Personalize o teste. Seu tempo será cronometrado.</p>

          <label className="pt-field-label">Tópicos</label>
          <div className="pt-topics">
            {cert.topics.map(t => (
              <button key={t}
                className={`pt-topic ${selTopics.includes(t) ? 'on' : ''}`}
                onClick={() => toggleTopic(t)}>{t}</button>
            ))}
          </div>
          <div className="pt-topics-actions">
            <button className="link-btn" onClick={() => setSelTopics(cert.topics)}>Selecionar todos</button>
            <button className="link-btn" onClick={() => setSelTopics([])}>Limpar</button>
          </div>

          <label className="pt-field-label">Número de questões: <b>{numQ}</b></label>
          <input type="range" min={5} max={60} step={5} value={numQ}
            onChange={e => setNumQ(Number(e.target.value))} className="pt-range" />
          <div className="pt-range-marks"><span>5</span><span>60</span></div>

          <label className="pt-ai">
            <input type="checkbox" checked={aiGen} onChange={e => setAiGen(e.target.checked)} />
            <Sparkles size={15} color="#6a1b9a" />
            <span>Gerar questões novas via IA (Claude Opus 4.8)</span>
          </label>
          {aiGen && (
            <div className="pt-ai-count">
              Quantas geradas (máx. 10): <b>{aiCount}</b>
              <input type="range" min={1} max={10} value={aiCount}
                onChange={e => setAiCount(Number(e.target.value))} className="pt-range" />
            </div>
          )}

          {error && <div className="pt-error">{error}</div>}
          <button className="btn btn-primary btn-lg pt-start"
            disabled={loading || selTopics.length === 0} onClick={start}>
            {loading ? <><Loader2 size={18} className="spinning" /> Criando…</> : 'Iniciar simulado'}
          </button>
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
        <div className="pt-run-bar">
          <span><Clock size={15} /> {fmtTime(elapsed)}</span>
          <span>Questão {idx + 1} de {session.questions.length}</span>
          <span>{answeredCount} respondidas</span>
        </div>
        <div className="pt-progress"><div style={{ width: `${(answeredCount / session.questions.length) * 100}%` }} /></div>

        <div className="card pt-question">
          <div className="pt-q-meta">
            <span className="pt-topic-tag">{q.topic}</span>
            {q.is_ai_generated && <span className="badge badge-ai">IA</span>}
            <span className="pt-diff">Dificuldade {q.difficulty}/5</span>
          </div>
          <h3 className="pt-q-text">{q.question_text}</h3>
          {multi && <p className="pt-multi-hint">Selecione todas as que se aplicam</p>}
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
          <button className="btn" disabled={idx === 0} onClick={() => setIdx(i => i - 1)}>Anterior</button>
          {idx < session.questions.length - 1
            ? <button className="btn btn-primary" onClick={() => setIdx(i => i + 1)}>Próxima</button>
            : <button className="btn btn-primary" disabled={loading} onClick={finish}>
                {loading ? <><Loader2 size={16} className="spinning" /> Corrigindo…</> : 'Finalizar simulado'}
              </button>}
        </div>
        <button className="link-btn pt-end-early" onClick={finish}>Encerrar agora</button>
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
            {pass ? 'Aprovado' : 'Reprovado'} · corte {result.pass_mark}%
          </div>
          <p>{result.correct} de {result.total} questões corretas</p>
          <div className="pt-stats">
            <div><b>{result.correct}</b><span>Corretas</span></div>
            <div><b>{result.total - result.correct}</b><span>Incorretas</span></div>
            <div><b>{fmtTime(result.duration_sec ?? 0)}</b><span>Tempo</span></div>
            {result.repeated_questions > 0 &&
              <div><b>{result.repeated_questions}</b><span>Repetidas</span></div>}
          </div>
        </div>

        <div className="card pt-topic-breakdown">
          <h3>Desempenho por tópico</h3>
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
          <button className="btn" onClick={() => setPhase('review')}><ListChecks size={16} /> Revisar respostas</button>
          <button className="btn btn-primary" onClick={reset}><RotateCcw size={16} /> Novo simulado</button>
        </div>
      </div>
    )
  }

  // ── REVIEW ──────────────────────────────────────────────────────────────────
  if (phase === 'review' && session && result) {
    return (
      <div className="pt-review">
        <div className="pt-review-head">
          <h3>Revisão — {result.correct}/{result.total} corretas</h3>
          <button className="btn" onClick={() => setPhase('results')}>← Voltar ao resultado</button>
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
                  {correct ? <><CheckCircle2 size={15} /> Correta</> : <><XCircle size={15} /> Incorreta</>}
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
                      {isCorrect && <span className="pt-tag ok">correta</span>}
                      {isSel && !isCorrect && <span className="pt-tag no">sua resposta (errada)</span>}
                    </div>
                  )
                })}
              </div>
              {q.explanation && <div className="pt-explain"><b>Explicação:</b> {q.explanation}</div>}
            </div>
          )
        })}
      </div>
    )
  }

  return null
}

function sorted(a: number[]) { return [...a].sort((x, y) => x - y) }
