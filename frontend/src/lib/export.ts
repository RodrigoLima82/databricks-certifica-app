// Utilitários de exportação (CSV client-side + download de blob)

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function csvCell(v: unknown): string {
  const s = v == null ? '' : String(v)
  // escapa aspas e envolve sempre (lida com ; , quebras de linha)
  return `"${s.replace(/"/g, '""')}"`
}

export function downloadCsv(filename: string, rows: (string | number | boolean | null)[][]) {
  const body = rows.map(r => r.map(csvCell).join(';')).join('\r\n')
  // BOM para o Excel reconhecer UTF-8 (acentos)
  const blob = new Blob(['﻿' + body], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, filename)
}

const LETTERS = 'ABCDEFGH'
export const optionLabels = (idxs: number[]) => idxs.map(i => LETTERS[i] ?? i).join(', ')
