import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import { Toaster } from "@/components/ui/sonner";
import LandingPage from "@/pages/LandingPage";
import JobRequestPage from "@/pages/JobRequestPage";
import TrackJobPage from "@/pages/TrackJobPage";
import AuthCallback from "@/pages/AuthCallback";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import AccountSettings from "@/pages/AccountSettings";
import AdminDashboard from "@/pages/AdminDashboard";
import DashboardRedirect from "@/pages/DashboardRedirect";
import ProtectedRoute from "@/components/shared/ProtectedRoute";

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/request" element={<JobRequestPage />} />
      <Route path="/track/:jobId" element={<TrackJobPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/account" element={<ProtectedRoute><AccountSettings /></ProtectedRoute>} />
      <Route path="/dashboard" element={<DashboardRedirect />} />
      <Route path="/admin/*" element={<ProtectedRoute role="admin"><AdminDashboard /></ProtectedRoute>} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRouter />
        <Toaster />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
