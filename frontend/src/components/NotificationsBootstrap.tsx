import { useNotifications } from '../hooks/useNotifications'

/** App kökünde WS/mock bildirimlerini aktif eder */
export function NotificationsBootstrap() {
  useNotifications()
  return null
}
