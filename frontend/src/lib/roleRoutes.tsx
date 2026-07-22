import { Navigate } from 'react-router-dom'
import { Role } from '../api/types'
import { useAuthStore } from '../store/authStore'

/** Rol bazlı varsayılan sayfa */
export function homePathForRole(role: string | null | undefined): string {
  switch (role) {
    case Role.SAHA_TEKNISYENI:
      return '/teknisyen'
    case Role.NOC_OPERATORU:
      return '/noc'
    case Role.SUPERVIZOR:
    case Role.ADMIN:
      return '/noc'
    case Role.MUSTERI:
      return '/musteri'
    default:
      return '/login'
  }
}

export function RoleHomeRedirect() {
  const role = useAuthStore((s) => s.user?.role)
  const token = useAuthStore((s) => s.accessToken)
  if (!token) return <Navigate to="/login" replace />
  return <Navigate to={homePathForRole(role)} replace />
}
