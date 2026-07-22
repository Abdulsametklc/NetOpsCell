import { create } from 'zustand'
import type { AppToast, ToastKind } from '../api/types'

interface ToastState {
  toasts: AppToast[]
  push: (kind: ToastKind, title: string, message?: string) => void
  dismiss: (id: string) => void
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (kind, title, message) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    set((s) => ({ toasts: [...s.toasts, { id, kind, title, message }] }))
    window.setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
    }, 4500)
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))
