// App.js
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { useAuth } from "./contexts/AuthContext";
import Navbar         from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage      from "./pages/LoginPage";
import HomePage       from "./pages/HomePage";
import DashboardPage  from "./pages/DashboardPage";
import AnalyzePage    from "./pages/AnalyzePage";
import CatalogPage    from "./pages/CatalogPage";
import AboutPage      from "./pages/AboutPage";
import "./App.css";

function AppRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="page-wrap">
      <Navbar />
      <main className="main-content">
        <Routes>
          {/* Public routes */}
          <Route path="/"        element={<HomePage    />} />
          <Route path="/catalog" element={<CatalogPage />} />
          <Route path="/about"   element={<AboutPage   />} />
          <Route path="/login"   element={
            isAuthenticated
              ? <Navigate to="/dashboard" replace />
              : <LoginPage />
          } />

          {/* Protected routes */}
          <Route path="/dashboard" element={
            <ProtectedRoute><DashboardPage /></ProtectedRoute>
          } />
          <Route path="/analyze" element={
            <ProtectedRoute><AnalyzePage /></ProtectedRoute>
          } />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="rfp-footer">
        <span>
          Elevate<span className="brand-accent">RFP</span>
          {" "}·{" "}
          Enterprise RFP Automation Platform
        </span>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
