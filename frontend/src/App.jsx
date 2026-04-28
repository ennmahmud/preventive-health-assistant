import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import ProtectedRoute from './components/layout/ProtectedRoute';
import SignInPage    from './pages/SignInPage';
import SignUpPage    from './pages/SignUpPage';
import DashboardPage from './pages/DashboardPage';
import AssessPage    from './pages/AssessPage';
import ChatPage      from './pages/ChatPage';
import ProgressPage  from './pages/ProgressPage';
import ProfilePage   from './pages/ProfilePage';
import SettingsPage  from './pages/SettingsPage';
import './index.css';

function AppRoutes() {
  const { isAuthenticated } = useAuth();
  return (
    <Routes>
      <Route path="/signin"   element={!isAuthenticated ? <SignInPage />  : <Navigate to="/dashboard" replace />} />
      <Route path="/signup"   element={!isAuthenticated ? <SignUpPage />  : <Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/assess"   element={<ProtectedRoute><AssessPage /></ProtectedRoute>} />
      <Route path="/chat"     element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
      <Route path="/progress"  element={<ProtectedRoute><ProgressPage /></ProtectedRoute>} />
      <Route path="/profile"   element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
      <Route path="/settings"  element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      <Route path="*"          element={<Navigate to={isAuthenticated ? '/dashboard' : '/signin'} replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
