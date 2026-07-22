import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { AuditLogRow, CreatePersonnelRequest } from '../api/types'
import { Role } from '../api/types'
import { createPersonnel, dashboardModeLabel, fetchAuditLogs } from '../api/dashboardApi'
import { ApiError } from '../api/client'
import { AppShell } from '../components/AppShell'
import { EmptyState, ErrorState, LoadingState } from '../components/UiStates'
import { Button, Card, Field, Input, Select } from '../components/ui'
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
        specializations: specText.split(',').map((s) => s.trim()).filter(Boolean),
        regions: regionText.split(',').map((s) => s.trim()).filter(Boolean),
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
      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-lg font-semibold">Personel hesabı oluştur</h2>
          <Card as="form" onSubmit={onCreate} className="space-y-3 p-4">
            {(
              [
                ['first_name', 'Ad'],
                ['last_name', 'Soyad'],
                ['email', 'E-posta'],
                ['password', 'Şifre'],
              ] as const
            ).map(([key, label]) => (
              <Field key={key} label={label}>
                <Input
                  type={key === 'password' ? 'password' : key === 'email' ? 'email' : 'text'}
                  value={form[key]}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                  required
                />
              </Field>
            ))}
            <Field label="Rol">
              <Select value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}>
                <option value={Role.SAHA_TEKNISYENI}>SAHA_TEKNISYENI</option>
                <option value={Role.NOC_OPERATORU}>NOC_OPERATORU</option>
                <option value={Role.SUPERVIZOR}>SUPERVIZOR</option>
                <option value={Role.ADMIN}>ADMIN</option>
              </Select>
            </Field>
            <Field label="Uzmanlıklar (virgülle)">
              <Input value={specText} onChange={(e) => setSpecText(e.target.value)} />
            </Field>
            <Field label="Bölgeler (virgülle)">
              <Input value={regionText} onChange={(e) => setRegionText(e.target.value)} />
            </Field>
            <Button type="submit" variant="primary" disabled={saving} className="w-full">
              {saving ? 'Kaydediliyor…' : 'Oluştur'}
            </Button>
          </Card>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">Audit log</h2>
            <button
              type="button"
              className="text-xs font-medium text-tc-navy-700 hover:underline dark:text-tc-yellow-400"
              onClick={() => void loadLogs()}
            >
              Yenile
            </button>
          </div>
          {loading && <LoadingState />}
          {error && <ErrorState message={error} />}
          {!loading && !error && logs.length === 0 && <EmptyState message="Kayıt yok." />}
          {!loading && logs.length > 0 && (
            <Card className="overflow-x-auto">
              <table className="w-full min-w-[28rem] text-left text-xs">
                <thead className="bg-slate-50 uppercase text-slate-500 dark:bg-tc-navy-950/60 dark:text-slate-400">
                  <tr>
                    <th className="px-3 py-2">Zaman</th>
                    <th className="px-3 py-2">Aksiyon</th>
                    <th className="px-3 py-2">Sonuç</th>
                    <th className="px-3 py-2">IP</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((row) => (
                    <tr key={row.id} className="border-t border-slate-200 dark:border-tc-navy-800">
                      <td className="px-3 py-2 text-slate-500 dark:text-slate-400">
                        {new Date(row.created_at).toLocaleString('tr-TR')}
                      </td>
                      <td className="px-3 py-2 font-mono text-tc-navy-800 dark:text-tc-yellow-400">
                        {row.action_type}
                      </td>
                      <td
                        className={`px-3 py-2 font-medium ${
                          row.result === 'SUCCESS'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-rose-600 dark:text-rose-400'
                        }`}
                      >
                        {row.result}
                      </td>
                      <td className="px-3 py-2 text-slate-400 dark:text-slate-500">{row.ip_address ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </section>
      </div>
    </AppShell>
  )
}
