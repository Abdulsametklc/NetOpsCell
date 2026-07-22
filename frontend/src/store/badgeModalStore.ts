import { create } from 'zustand'

export interface BadgeModalState {
  open: boolean
  badgeCode: string | null
  badgeName: string | null
  show: (badgeCode: string, badgeName?: string) => void
  close: () => void
}

export const useBadgeModalStore = create<BadgeModalState>((set) => ({
  open: false,
  badgeCode: null,
  badgeName: null,
  show: (badgeCode, badgeName) =>
    set({ open: true, badgeCode, badgeName: badgeName ?? badgeCode }),
  close: () => set({ open: false, badgeCode: null, badgeName: null }),
}))
