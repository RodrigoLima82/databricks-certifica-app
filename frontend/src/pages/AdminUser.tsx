import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  CheckCircle2, XCircle, ChevronDown, ChevronRight, RefreshCw,
  FileText, FileSpreadsheet, Loader2,
} from 'lucide-react'
import {
  getAdminUserAttempts, getAdminSession, getAdminSessionPdf,
} from '@/services/api'
import { downloadCsv, downloadBlob, optionLabels } from '@/lib/export'
import { useT, useI18n } from '@/i18n'
import type { Attempt } from '@/types'
import './History.css'

const LOCALE = { es: 'es-CL', pt: 'pt-BR', en: 'en-US' } as const

function AnswersPanel({ sessionId }: { sessionId: string }) {
  const t = useT()
  const { data, isLoading } = useQuery({
    queryKey: ['admin-session', sessionId],
    queryFn: () => getAdminSession(sessionId),
  })
  if (isLoading) return <div className="spinner" />
  if (!data) return null
  return (
    <div className="au-answers">
      {data.answers.map((a, i) => (
        <div key={a.question_id} className="au-q">
          <div className="au-q-head">
            <span className="pt-topic-tag">{a.topic}</span>
            {a.is_ai_generated && <span className="badge badge-ai">IA</span>}
            <span className={`pt-verdict ${a.is_correct ? 'ok' : 'no'}`}>
              {a.is_correct ? <><CheckCircle2 size={14} /> {t('adminUser.correct')}</> : <><XCircle size={14} /> {t('adminUser.incorrect')}</>}
            </span>
          </div>
          <p className="au-q-text"><b>{i + 1}.</b> {a.question_text}</p>
          <div className="pt-rev-opts">
            {a.options.map((opt, oi) => {
              const isCorrect = a.correct_answers.includes(oi)
              const isSel = a.selected.includes(oi)
              return (
                <div key={oi} className={`pt-rev-opt ${isCorrect ? 'correct' : ''} ${isSel && !isCorrect ? 'wrong' : ''}`}>
                  <span>{opt}</span>
                  {isCorrect && <span className="pt-tag ok">{t('adminUser.correctTag')}</span>}
                  {isSel && !isCorrect && <span className="pt-tag no">{t('adminUser.participantAnswer')}</span>}
                </div>
              )
            })}
          </div>
          {a.explanation && <div className="pt-explain"><b>{t('adminUser.explanation')}</b> {a.explanation}</div>}
        </div>
      ))}
    </div>
  )
}

export default function AdminUser() {
  const { email = '' } = useParams()
  const navigate = useNavigate()
  const decoded = decodeURIComponent(email)
  const { data, isLoading } = useQuery({
    queryKey: ['admin-user', decoded],
    queryFn: () => getAdminUserAttempts(decoded),
  })
  const t = useT()
  const { lang } = useI18n()
  const [open, setOpen] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)   // `${sid}:csv|pdf`

  if (isLoading) return <div className="spinner" />
  const attempts = data?.attempts ?? []
  const passMark = data?.pass_mark ?? 70
  const fmt = (s?: string) => s ? new Date(s).toLocaleString(LOCALE[lang]) : '—'
  const slug = decoded.split('@')[0]

  function exportSummary() {
    const c = (k: string) => t(`adminUser.csv.${k}`)
    const rows: (string | number | boolean)[][] = [
      [c('participant'), c('email'), c('certification'), c('date'), c('scorePct'), c('hits'), c('total'), c('result'), c('repeated')],
      ...attempts.map(a => [
        decoded.split('@')[0], decoded, a.certification_name ?? a.certification_id,
        fmt(a.created_at), a.score_pct, a.correct, a.total,
        a.passed ? t('adminUser.approved') : t('adminUser.reproved'), a.repeated_questions,
      ]),
    ]
    downloadCsv(`${c('summaryFile')}_${slug}.csv`, rows)
  }

  async function exportAttemptCsv(a: Attempt) {
    setBusy(`${a.session_id}:csv`)
    const c = (k: string) => t(`adminUser.csv.${k}`)
    try {
      const detail = await getAdminSession(a.session_id)
      const header = [
        [c('participant'), decoded], [c('certification'), a.certification_name ?? a.certification_id],
        [c('date'), fmt(a.created_at)], [c('score'), `${a.score_pct}%`],
        [c('result'), a.passed ? t('adminUser.approved') : t('adminUser.reproved')],
        [c('hits'), `${a.correct}/${a.total}`], [c('repeated'), a.repeated_questions], [],
      ]
      const table: (string | number | boolean)[][] = [
        [c('num'), c('topic'), c('question'), c('options'), c('participantAnswer'), c('correct'), c('gotIt'), c('explanation')],
        ...detail.answers.map((ans, i) => [
          i + 1, ans.topic, ans.question_text,
          ans.options.map((o, oi) => `${'ABCDEFGH'[oi]}) ${o}`).join(' | '),
          optionLabels(ans.selected), optionLabels(ans.correct_answers),
          ans.is_correct ? c('yes') : c('no'), ans.explanation,
        ]),
      ]
      downloadCsv(`${c('testFile')}_${slug}_${a.session_id.slice(0, 8)}.csv`, [...header, ...table])
    } finally { setBusy(null) }
  }

  async function exportAttemptPdf(a: Attempt) {
    setBusy(`${a.session_id}:pdf`)
    try {
      const blob = await getAdminSessionPdf(a.session_id)
      downloadBlob(blob, `test_${slug}_${a.session_id.slice(0, 8)}.pdf`)
    } finally { setBusy(null) }
  }

  return (
    <div>
      <button className="link-btn au-back" onClick={() => navigate('/admin')}>{t('adminUser.backToPanel')}</button>
      <div className="au-title-row">
        <div>
          <h1 className="hist-title">{decoded}</h1>
          <p className="muted hist-sub">{t('adminUser.attemptsCount', { n: attempts.length, m: passMark })}</p>
        </div>
        {attempts.length > 0 &&
          <button className="btn" onClick={exportSummary}>
            <FileSpreadsheet size={16} /> {t('adminUser.exportSummary')}
          </button>}
      </div>

      <div className="au-list">
        {attempts.map(a => {
          const isOpen = open === a.session_id
          return (
            <div key={a.session_id} className="card au-attempt">
              <div className="au-attempt-bar">
                <button className="au-attempt-head" onClick={() => setOpen(isOpen ? null : a.session_id)}>
                  {isOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                  <span className="au-cert">{a.certification_name ?? a.certification_id}</span>
                  <span className="au-date">{fmt(a.created_at)}</span>
                  <span className="au-score"><b>{a.score_pct}%</b> ({a.correct}/{a.total})</span>
                  {a.repeated_questions > 0 &&
                    <span className="hist-rep"><RefreshCw size={12} /> {a.repeated_questions}</span>}
                  {a.passed
                    ? <span className="hist-badge ok">{t('adminUser.approved')}</span>
                    : <span className="hist-badge no">{t('adminUser.reproved')}</span>}
                </button>
                <div className="au-exports">
                  <button className="au-exp-btn" title="Exportar CSV"
                    disabled={busy === `${a.session_id}:csv`} onClick={() => exportAttemptCsv(a)}>
                    {busy === `${a.session_id}:csv` ? <Loader2 size={14} className="spinning" /> : <FileSpreadsheet size={14} />} CSV
                  </button>
                  <button className="au-exp-btn" title="Exportar PDF"
                    disabled={busy === `${a.session_id}:pdf`} onClick={() => exportAttemptPdf(a)}>
                    {busy === `${a.session_id}:pdf` ? <Loader2 size={14} className="spinning" /> : <FileText size={14} />} PDF
                  </button>
                </div>
              </div>
              {isOpen && <AnswersPanel sessionId={a.session_id} />}
            </div>
          )
        })}
      </div>
    </div>
  )
}
