import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Role } from './api/types'
import { RoleHomeRedirect } from './lib/roleRoutes'
import { CustomerHomePage } from './pages/CustomerHomePage'
import { LoginPage } from './pages/LoginPage'
import { TechnicianDashboardPage } from './pages/TechnicianDashboardPage'

export default function App() {
  return (
    <BrowserRouter>
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
            <ProtectedRoute
              roles={[
                Role.SAHA_TEKNISYENI,
                Role.NOC_OPERATORU,
                Role.SUPERVIZOR,
                Role.ADMIN,
              ]}
            >
              <TechnicianDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
