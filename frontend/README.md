# NetOpsCell — Frontend

React UI for NetOpsCell (Turkcell CodeNight 2026). Talks to backend via Gateway when available; in local dev uses Vite proxy + optional mocks so UI can ship without waiting on every service.

## Stack

- Vite 8 + React 19 + TypeScript
- Tailwind CSS v4
- react-router-dom, Zustand, Recharts
- nginx static image for Docker (`Dockerfile`)

## Quick start (dev, mocks OK)

```bash
cd frontend
cp .env.example .env   # adjust flags as needed
npm install
npm run dev
```

App: http://localhost:5173

Docker Desktop **not required** for UI-only work. Use mocks (`VITE_USE_*_MOCK=true`) until backends are up on a machine with Docker.

## Scripts

| Command        | Purpose                          |
|----------------|----------------------------------|
| `npm run dev`  | Vite dev server (port 5173)      |
| `npm run build`| `tsc -b` + production bundle     |
| `npm run preview` | Serve `dist/` locally         |
| `npm run lint` | oxlint                           |

## Environment

See `.env.example`. Important variables:

| Variable | Meaning |
|----------|---------|
| `VITE_API_BASE_URL` | Empty in dev → same-origin + Vite proxy. With Gateway: `http://localhost:8000` |
| `VITE_USE_AUTH_MOCK` | `true` = fake login (no Identity/Gateway) |
| `VITE_USE_INCIDENT_MOCK` | `true` = mock incidents/telemetry |
| `VITE_USE_GAME_MOCK` | `true` = mock leaderboard/profile/points |
| `VITE_USE_MESSAGE_MOCK` | `true` = mock in-incident messages |
| `VITE_USE_DASHBOARD_MOCK` | `true` = mock supervisor stats / admin audit (default until APIs exist) |
| `VITE_USE_WS_MOCK` | `true` = fake notification events |
| `VITE_WS_URL` | Optional real Notification Hub WS URL |
| `VITE_INJECT_USER_HEADERS` | When auth is mock, inject `X-User-Id` / `X-User-Role` for Incident |

**Recommended without Docker:** all `VITE_USE_*_MOCK=true`.

**With compose backends up:** set incident/game mocks to `false`; keep message/dashboard/auth mocks as needed until those endpoints + Gateway are ready.

Identity listens on **:8001**; Vite still proxies `/api/v1/auth` → **:8000** (Gateway). Until Gateway exists, keep `VITE_USE_AUTH_MOCK=true` or point the proxy at `:8001`.

## Dev proxy (Gateway yokken)

`vite.config.ts` forwards:

| Path prefix | Target |
|-------------|--------|
| `/api/v1/telemetry`, `/api/v1/incidents` | `localhost:8002` (Incident) |
| `/api/v1/ai` | `localhost:8003` (AI) |
| `/api/v1/game` | `localhost:8004` (Gamification) |
| `/api/v1/auth`, `/api/v1/ws` | `localhost:8000` (Gateway — TBD) |

## Live stack (Docker’lı makine)

Repo kökünden:

```bash
docker compose up --build
```

- Frontend container: http://localhost:3000 (API base baked as Gateway `:8000`)
- Or keep `npm run dev` on host and hit proxied service ports from compose.

Full e2e (real login + WS) needs Gateway (Kişi 1) + healthy identity/incident/ai/game.

## Routes & roles

| Path | Roles |
|------|--------|
| `/login` | public |
| `/teknisyen` | SAHA_TEKNISYENI, SUPERVIZOR, ADMIN |
| `/noc` | NOC_OPERATORU, SUPERVIZOR, ADMIN |
| `/dashboard` | SUPERVIZOR, ADMIN |
| `/admin` | ADMIN |
| `/liderlik`, `/profil` | authenticated |
| `/musteri` | MUSTERI (stub) |

### Mock login (auth mock on)

Password free. Role from email substring:

| Email hint | Role | Lands on |
|------------|------|----------|
| `teknisyen@…` | SAHA_TEKNISYENI | `/teknisyen` |
| `noc@…` | NOC_OPERATORU | `/noc` |
| `super@…` | SUPERVIZOR | `/dashboard` |
| `admin@…` | ADMIN | `/admin` |
| GSM+OTP tab | MUSTERI | `/musteri` |

## Features (CP1–CP6)

- Login (personel + müşteri sekmesi), token store, role guards
- Technician dashboard (status transitions, resolve)
- NOC: telemetry form, predict → open incident
- Leaderboard + profile (points / level / badges)
- SLA badge, message thread UI, notification toast/modal (WS or mock)
- Supervisor dashboard (Recharts: category pie, priority, SLA %, AI accuracy, team table, unassigned queue + assign)
- Admin: create personnel + audit log table

## Contracts

API shapes follow `docs/CONTRACTS.md`. Types live under `src/api/types/`.

## Owner

Kişi 3 — only `frontend/` (shared root files need team notice before edits).
