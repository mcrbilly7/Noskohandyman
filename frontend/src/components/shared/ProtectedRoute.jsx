import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export default function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (location.state?.user) {
    if (role && location.state.user.role !== role && location.state.user.role !== "admin") {
      return <Navigate to="/" replace />;
    }
    return children;
  }
  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="overline">Loading…</div></div>;
  if (!user) return <Navigate to="/" replace />;
  if (role && user.role !== role && user.role !== "admin") return <Navigate to="/" replace />;
  return children;
}
