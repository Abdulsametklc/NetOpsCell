import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { AuditLogRow, CreatePersonnelRequest } from '../api/types'
import { Role } from '../api/types'
import {
  createPersonnel,
  dashboardModeLabel,
  fetchAuditLogs,
} from '../api/dashboardApi'
import { ApiError } from '../api/client'
import { AppShell } from '../components/AppShell'
import { EmptyState, ErrorState, LoadingState } from '../components/UiStates'
import { useToastStore } from '../store/toastStore'

const emptyForm: CreatePersonnelRequest = {
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: Role.SAHA_TEKNISYENI,
  specializations: ['DONANIM'],
  regions: ['IST-AVRUPA'],
}

export function AdminPanelPage() {
  const pushToast = useToastStore((s) => s.push)
  const [logs, setLogs] = useState<AuditLogRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState<CreatePersonnelRequest>(emptyForm)
  const [specText, setSpecText] = useState('DONANIM,ISINMA')
  const [regionText, setRegionText] = useState('IST-AVRUPA')
  const [saving, setSaving] = useState(false)

  async function loadLogs() {
    setLoading(true)
    setError(null)
    try {
      setLogs(await fetchAuditLogs())
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : 'Audit alınamadı')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadLogs()
  }, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const body: CreatePersonnelRequest = {
        ...form,
        specializations: specText
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        regions: regionText
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      }
      await createPersonnel(body)
      pushToast('success', 'Personel oluşturuldu', body.email)
      setForm(emptyForm)
    } catch (err) {
      pushToast('warning', 'Oluşturma başarısız', err instanceof Error ? err.message : 'Hata')
    } finally {
      setSaving(false)
    }
  }

  return (
    <AppShell title="NetOpsCell — Admin" subtitle={dashboardModeLabel()}>
      <div className="grid gap-8 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-lg font-medium">Personel hesabı oluştur</h2>
          <form
            onSubmit={onCreate}
            className="space-y-3 rounded-lg border border-slate-800 bg-slate-900/40 p-4"
          >
            {(
              [
                ['first_name', 'Ad'],
                ['last_name', 'Soyad'],
                ['email', 'E-posta'],
                ['password', 'Şifre'],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="block text-sm">
                <span className="text-slate-400">{label}</span>
                <input
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                  type={key === 'password' ? 'password' : key === 'email' ? 'email' : 'text'}
                  value={form[key]}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                  required
                />
              </label>
            ))}
            <label className="block text-sm">
              <span className="text-slate-400">Rol</span>
              <select
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                value={form.role}
                onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
              >
                <option value={Role.SAHA_TEKNISYENI}>SAHA_TEKNISYENI</option>
                <option value={Role.NOC_OPERATORU}>NOC_OPERATORU</option>
                <option value={Role.SUPERVIZOR}>SUPERVIZOR</option>
                <option value={Role.ADMIN}>ADMIN</option>
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-slate-400">Uzmanlıklar (virgülle)</span>
              <input
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                value={specText}
                onChange={(e) => setSpecText(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-400">Bölgeler (virgülle)</span>
              <input
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
                value={regionText}
                onChange={(e) => setRegionText(e.target.value)}
              />
            </label>
            <button
              type="submit"
              disabled={saving}
              className="w-full rounded bg-sky-600 py-2 text-sm font-medium hover:bg-sky-500 disabled:opacity-60"
            >
              {saving ? 'Kaydediliyor…' : 'Oluştur'}
            </button>
          </form>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="text-lg font-medium">Audit log</h2>
            <button
              type="button"
              className="text-xs text-sky-400 hover:underline"
              onClick={() => void loadLogs()}
            >
              Yenile
            </button>
          </div>
          {loading && <LoadingState />}
          {error && <ErrorState message={error} />}
          {!loading && !error && logs.length === 0 && (
            <EmptyState message="Kayıt yok." />
          )}
          {!loading && logs.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-slate-800">
              <table className="w-full min-w-[28rem] text-left text-xs">
                <thead className="bg-slate-900/80 uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Zaman</th>
                    <th className="px-3 py-2">Aksiyon</th>
                    <th className="px-3 py-2">Sonuç</th>
                    <th className="px-3 py-2">IP</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((row) => (
                    <tr key={row.id} className="border-t border-slate-800">
                      <td className="px-3 py-2 text-slate-400">
                        {new Date(row.created_at).toLocaleString('tr-TR')}
                      </td>
                      <td className="px-3 py-2 font-mono text-sky-300">{row.action_type}</td>
                      <td
                        className={`px-3 py-2 ${
                          row.result === 'SUCCESS' ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {row.result}
                      </td>
                      <td className="px-3 py-2 text-slate-500">{row.ip_address ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  )
}
