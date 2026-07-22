/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_USE_AUTH_MOCK: string
  readonly VITE_USE_INCIDENT_MOCK: string
  readonly VITE_USE_GAME_MOCK: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
