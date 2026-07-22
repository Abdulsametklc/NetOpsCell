import type { AssignResponse, ResponseEnvelope } from '../types'

export const mockAssignSuccess: ResponseEnvelope<AssignResponse> = {
  success: true,
  data: {
    queued: false,
    team_id: 'team-42',
    team_name: 'IST-AVRUPA-A',
    score: 0.87,
    components: {
      uzmanlik_eslesme: 1,
      mesafe_yakinlik: 0.8,
      bosluk_orani: 0.7,
    },
  },
  error: null,
}

export const mockAssignQueued: ResponseEnvelope<AssignResponse> = {
  success: true,
  data: {
    queued: true,
    team_id: null,
    team_name: null,
    score: null,
    components: null,
  },
  error: null,
}
