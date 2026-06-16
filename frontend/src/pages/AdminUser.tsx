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
import type { Attempt } from '@/types'
import './History.css'

function AnswersPanel({ sessionId }: { sessionId: string }) {
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
              {a.is_correct ? <><CheckCircle2 size={14} /> Correta</> : <><XCircle size={14} /> Incorreta</>}
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
                  {isCorrect && <span className="pt-tag ok">correta</span>}
                  {isSel && !isCorrect && <span className="pt-tag no">resposta do aluno</span>}
                </div>
              )
            })}
          </div>
          {a.explanation && <div className="pt-explain"><b>Explicação:</b> {a.explanation}</div>}
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
  const [open, setOpen] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)   // `${sid}:csv|pdf`

  if (isLoading) return <div className="spinner" />
  const attempts = data?.attempts ?? []
  const passMark = data?.pass_mark ?? 70
  const fmt = (s?: string) => s ? new Date(s).toLocaleString('pt-BR') : '—'
  const slug = decoded.split('@')[0]

  function exportSummary() {
    const rows: (string | number | boolean)[][] = [
      ['Aluno', 'E-mail', 'Certificação', 'Data', 'Score (%)', 'Acertos', 'Total', 'Resultado', 'Repetidas'],
      ...attempts.map(a => [
        decoded.split('@')[0], decoded, a.certification_name ?? a.certification_id,
        fmt(a.created_at), a.score_pct, a.correct, a.total,
        a.passed ? 'Aprovado' : 'Reprovado', a.repeated_questions,
      ]),
    ]
    downloadCsv(`resumo_${slug}.csv`, rows)
  }

  async function exportAttemptCsv(a: Attempt) {
    setBusy(`${a.session_id}:csv`)
    try {
      const detail = await getAdminSession(a.session_id)
      const header = [
        ['Aluno', decoded], ['Certificação', a.certification_name ?? a.certification_id],
        ['Data', fmt(a.created_at)], ['Score', `${a.score_pct}%`],
        ['Resultado', a.passed ? 'Aprovado' : 'Reprovado'],
        ['Acertos', `${a.correct}/${a.total}`], ['Repetidas', a.repeated_questions], [],
      ]
      const table: (string | number | boolean)[][] = [
        ['#', 'Tópico', 'Questão', 'Opções', 'Resposta do aluno', 'Correta', 'Acertou?', 'Explicação'],
        ...detail.answers.map((ans, i) => [
          i + 1, ans.topic, ans.question_text,
          ans.options.map((o, oi) => `${'ABCDEFGH'[oi]}) ${o}`).join(' | '),
          optionLabels(ans.selected), optionLabels(ans.correct_answers),
          ans.is_correct ? 'Sim' : 'Não', ans.explanation,
        ]),
      ]
      downloadCsv(`teste_${slug}_${a.session_id.slice(0, 8)}.csv`, [...header, ...table])
    } finally { setBusy(null) }
  }

  async function exportAttemptPdf(a: Attempt) {
    setBusy(`${a.session_id}:pdf`)
    try {
      const blob = await getAdminSessionPdf(a.session_id)
      downloadBlob(blob, `teste_${slug}_${a.session_id.slice(0, 8)}.pdf`)
    } finally { setBusy(null) }
  }

  return (
    <div>
      <button className="link-btn au-back" onClick={() => navigate('/admin')}>← Voltar ao painel</button>
      <div className="au-title-row">
        <div>
          <h1 className="hist-title">{decoded}</h1>
          <p className="muted hist-sub">{attempts.length} tentativa(s) · corte {passMark}%.</p>
        </div>
        {attempts.length > 0 &&
          <button className="btn" onClick={exportSummary}>
            <FileSpreadsheet size={16} /> Exportar resumo (CSV)
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
                    ? <span className="hist-badge ok">Aprovado</span>
                    : <span className="hist-badge no">Reprovado</span>}
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
