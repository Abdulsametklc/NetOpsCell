import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { BadgeModal } from './components/BadgeModal'
import { NotificationsBootstrap } from './components/NotificationsBootstrap'
import { ProtectedRoute } from './components/ProtectedRoute'
import { ToastHost } from './components/ToastHost'
import { Role } from './api/types'
import { RoleHomeRedirect } from './lib/roleRoutes'
import { CustomerHomePage } from './pages/CustomerHomePage'
import { LeaderboardPage } from './pages/LeaderboardPage'
import { LoginPage } from './pages/LoginPage'
import { NocDashboardPage } from './pages/NocDashboardPage'
import { ProfilePage } from './pages/ProfilePage'
import { TechnicianDashboardPage } from './pages/TechnicianDashboardPage'

export default function App() {
  return (
    <BrowserRouter>
      <NotificationsBootstrap />
      <ToastHost />
      <BadgeModal />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<RoleHomeRedirect />} />
        <Route
          path="/musteri"
          element={
            <ProtectedRoute roles={[Role.MUSTERI]}>
              <CustomerHomePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/teknisyen"
          element={
            <ProtectedRoute roles={[Role.SAHA_TEKNISYENI, Role.SUPERVIZOR, Role.ADMIN]}>
              <TechnicianDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/noc"
          element={
            <ProtectedRoute
              roles={[Role.NOC_OPERATORU, Role.SUPERVIZOR, Role.ADMIN]}
            >
              <NocDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/liderlik"
          element={
            <ProtectedRoute>
              <LeaderboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profil"
          element={
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
