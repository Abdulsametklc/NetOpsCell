import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { IncidentListItem } from '../api/types'
import { listMyIncidents, reportIncident } from '../api/incidentApi'
import { AppShell } from '../components/AppShell'
import { Button, Card, Textarea } from '../components/ui'
import { EmptyState, LoadingState } from '../components/UiStates'
import { useAuthStore } from '../store/authStore'
import { useToastStore } from '../store/toastStore'

const STATUS_LABELS: Record<string, string> = {
  YENI: 'Kaydınız alındı, atama bekliyor',
  ATANDI: 'Saha ekibine atandı',
  YOLDA: 'Ekip sahaya gidiyor',
  MUDAHALE_EDILIYOR: 'Müdahale ediliyor',
  PARCA_BEKLENIYOR: 'Yedek parça bekleniyor',
  COZULDU: 'Çözüldü',
  KAPANDI: 'Kapatıldı',
}

export function CustomerHomePage() {
  const user = useAuthStore((s) => s.user)
  const pushToast = useToastStore((s) => s.push)

  const [myIncidents, setMyIncidents] = useState<IncidentListItem[]>([])
  const [myLoading, setMyLoading] = useState(true)
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function loadMyIncidents() {
    setMyLoading(true)
    try {
      setMyIncidents(await listMyIncidents())
    } catch {
      // sessizce yut - form yine de gonderilebilir, kayit listesi ikincil
    } finally {
      setMyLoading(false)
    }
  }

  useEffect(() => {
    void loadMyIncidents()
  }, [])

  async function onSubmitReport(e: FormEvent) {
    e.preventDefault()
    if (description.trim().length < 5) {
      pushToast('warning', 'Açıklama çok kısa', 'Lütfen sorununuzu birkaç kelimeyle açıklayın (en az 5 karakter).')
      return
    }
    setSubmitting(true)
    try {
      await reportIncident(description.trim())
      setDescription('')
      pushToast('success', 'Arıza kaydınız alındı', 'Ekibimiz en kısa sürede inceleyecek.')
      await loadMyIncidents()
    } catch (err) {
      pushToast('warning', 'Bildirim gönderilemedi', err instanceof Error ? err.message : 'Hata')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppShell title="NetOpsCell — Müşteri" subtitle="Arıza bildirimi">
      <Card className="mb-6 flex flex-col items-center gap-2 p-8 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-tc-yellow-100 text-2xl dark:bg-tc-yellow-500/15">
          📶
        </span>
        <h1 className="text-2xl font-bold">Hoş geldiniz{user?.first_name ? `, ${user.first_name}` : ''}</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Hattınızla ilgili yaşadığınız sorunu aşağıdan bildirebilir, kayıtlarınızın durumunu takip edebilirsiniz.
        </p>
      </Card>

      <Card className="p-5">
        <h2 className="mb-3 text-lg font-semibold">Arıza bildir</h2>
        <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
          Hattınızla ilgili yaşadığınız sorunu kısaca anlatın, ekibimiz inceleyip size en yakın saha
          ekibini yönlendirsin.
        </p>
        <form onSubmit={onSubmitReport} className="space-y-3">
          <Textarea
            rows={3}
            placeholder="Örn: İki gündür internetim çok yavaş ve sürekli kopuyor."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <Button type="submit" variant="primary" disabled={submitting}>
            {submitting ? 'Gönderiliyor…' : 'Bildir'}
          </Button>
        </form>
      </Card>

      <Card className="mt-6 p-5">
        <h2 className="mb-3 text-lg font-semibold">Kayıtlarım</h2>
        {myLoading && <LoadingState message="Kayıtlarınız yükleniyor…" />}
        {!myLoading && myIncidents.length === 0 && <EmptyState message="Henüz bir arıza bildirmediniz." />}
        {!myLoading && myIncidents.length > 0 && (
          <ul className="space-y-3">
            {myIncidents.map((i) => (
              <li
                key={i.id}
                className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm dark:border-tc-navy-800 dark:bg-tc-navy-950/50"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono text-tc-navy-700 dark:text-tc-yellow-400">{i.incident_number}</span>
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                    {STATUS_LABELS[String(i.current_status)] ?? i.current_status}
                  </span>
                </div>
                {i.customer_description && (
                  <p className="mt-1 text-slate-600 dark:text-slate-300">{i.customer_description}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </AppShell>
  )
}
