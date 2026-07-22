import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { BadgeModal } from './components/BadgeModal'
import { NotificationsBootstrap } from './components/NotificationsBootstrap'
import { ProtectedRoute } from './components/ProtectedRoute'
import { ToastHost } from './components/ToastHost'
import { Role } from './api/types'
import { ThemeProvider } from './lib/theme'
import { RoleHomeRedirect } from './lib/roleRoutes'
import { CustomerHomePage } from './pages/CustomerHomePage'
import { AdminPanelPage } from './pages/AdminPanelPage'
import { LeaderboardPage } from './pages/LeaderboardPage'
import { LoginPage } from './pages/LoginPage'
import { NocDashboardPage } from './pages/NocDashboardPage'
import { ProfilePage } from './pages/ProfilePage'
import { SupervisorDashboardPage } from './pages/SupervisorDashboardPage'
import { TechnicianDashboardPage } from './pages/TechnicianDashboardPage'

export default function App() {
  return (
    <ThemeProvider>
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
          path="/dashboard"
          element={
            <ProtectedRoute roles={[Role.SUPERVIZOR, Role.ADMIN]}>
              <SupervisorDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute roles={[Role.ADMIN]}>
              <AdminPanelPage />
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
    </ThemeProvider>
  )
}
