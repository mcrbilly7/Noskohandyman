import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export default function DashboardRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="overline">Loading…</div></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "admin" || user.role === "developer") return <Navigate to="/admin" replace />;
  return <Navigate to="/account" replace />;
}
