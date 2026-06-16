import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Loader2, GraduationCap } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { authStatus } from '@/services/api'
import './Login.css'

export default function Login() {
  const { login, register } = useAuth()
  const { data: status } = useQuery({ queryKey: ['auth-status'], queryFn: authStatus })
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canRegister = status?.allow_self_register ?? true

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null); setLoading(true)
    try {
      if (mode === 'register') await register(name.trim(), email.trim(), password)
      else await login(email.trim(), password)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Falha na autenticação.')
    } finally { setLoading(false) }
  }

  return (
    <div className="login-page">
      <div className="login-card card">
        <div className="login-brand">
          <img src="/databricks-logo.svg" alt="Databricks" className="login-logo" />
          <span className="login-brand-name">Certifica</span>
        </div>
        <p className="login-sub">
          <GraduationCap size={15} /> Hub de Preparação para Certificações Databricks
        </p>

        <div className="login-tabs">
          <button className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); setError(null) }}>
            Entrar
          </button>
          {canRegister && (
            <button className={mode === 'register' ? 'active' : ''} onClick={() => { setMode('register'); setError(null) }}>
              Criar conta
            </button>
          )}
        </div>

        <form onSubmit={submit} className="login-form">
          {mode === 'register' && (
            <label>
              Nome completo
              <input value={name} onChange={e => setName(e.target.value)}
                placeholder="Seu nome" required autoComplete="name" />
            </label>
          )}
          <label>
            E-mail
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              required autoComplete="email" />
          </label>
          <label>
            Senha
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" required minLength={6}
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'} />
          </label>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="btn btn-primary btn-lg login-submit" disabled={loading}>
            {loading ? <><Loader2 size={18} className="spinning" /> Aguarde…</>
              : mode === 'register' ? 'Criar conta e entrar' : 'Entrar'}
          </button>
        </form>

        <p className="login-foot">
          Seu desempenho é registrado para acompanhamento do treinamento. Nota de corte: {status?.pass_mark ?? 70}%.
        </p>
      </div>
    </div>
  )
}
