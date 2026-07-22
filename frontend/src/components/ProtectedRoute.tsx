import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuthStore } from '../store/authStore'
import type { Role } from '../api/types'

interface ProtectedRouteProps {
  children: ReactNode
  roles?: Array<Role | string>
}

export function ProtectedRoute({ children, roles }: ProtectedRouteProps) {
  const location = useLocation()
  const accessToken = useAuthStore((s) => s.accessToken)
  const user = useAuthStore((s) => s.user)

  if (!accessToken) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (roles && roles.length > 0) {
    const role = user?.role
    if (!role || !roles.includes(role)) {
      return <Navigate to="/" replace />
    }
  }

  return children
}
