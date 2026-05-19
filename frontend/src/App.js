import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import { Toaster } from "@/components/ui/sonner";
import LandingPage from "@/pages/LandingPage";
import JobRequestPage from "@/pages/JobRequestPage";
import WorkerSignupPage from "@/pages/WorkerSignupPage";
import MarketerSignupPage from "@/pages/MarketerSignupPage";
import AuthCallback from "@/pages/AuthCallback";
import WorkerDashboard from "@/pages/WorkerDashboard";
import MarketerDashboard from "@/pages/MarketerDashboard";
import AdminDashboard from "@/pages/AdminDashboard";
import DashboardRedirect from "@/pages/DashboardRedirect";
import ProtectedRoute from "@/components/shared/ProtectedRoute";

function AppRouter() {
  const location = useLocation();
  // Synchronously detect session_id (URL fragment) for OAuth callback.
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/request" element={<JobRequestPage />} />
      <Route path="/join/worker" element={<WorkerSignupPage />} />
      <Route path="/join/marketer" element={<MarketerSignupPage />} />
      <Route path="/dashboard" element={<DashboardRedirect />} />
      <Route path="/dashboard/worker" element={<ProtectedRoute><WorkerDashboard /></ProtectedRoute>} />
      <Route path="/dashboard/marketer" element={<ProtectedRoute><MarketerDashboard /></ProtectedRoute>} />
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
