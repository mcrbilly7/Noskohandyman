import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Zap, LogOut, User } from "lucide-react";

export default function Navbar() {
  const { user, login, logout } = useAuth();
  const loc = useLocation();
  const onAdmin = loc.pathname.startsWith("/admin") || loc.pathname.startsWith("/dashboard");

  if (onAdmin) return null;

  return (
    <header className="border-b-2 border-black bg-white sticky top-0 z-30">
      <div className="max-w-[1400px] mx-auto flex items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-2" data-testid="nav-home-link">
          <div className="w-9 h-9 bg-[#FFD600] border-2 border-black flex items-center justify-center">
            <Zap className="w-5 h-5" strokeWidth={3} />
          </div>
          <div>
            <div className="font-display text-xl tracking-tighter leading-none">NOSKO</div>
            <div className="overline text-[10px] text-neutral-600">HANDYMAN CO.</div>
          </div>
        </Link>
        <nav className="hidden md:flex items-center gap-8 overline">
          <Link to="/request" data-testid="nav-request-link">Request Job</Link>
          <Link to="/join/worker" data-testid="nav-worker-link">Become Handyman</Link>
          <Link to="/join/marketer" data-testid="nav-marketer-link">Marketer Program</Link>
        </nav>
        <div className="flex items-center gap-3">
          {user ? (
            <>
              <Link
                to={user.role === "admin" ? "/admin" : user.role === "worker" ? "/dashboard/worker" : user.role === "marketer" ? "/dashboard/marketer" : "/dashboard"}
                className="btn-brutal ghost"
                data-testid="nav-dashboard-btn"
              >
                <User className="w-4 h-4" /> Dashboard
              </Link>
              <button className="btn-brutal" onClick={logout} data-testid="nav-logout-btn">
                <LogOut className="w-4 h-4" />
              </button>
            </>
          ) : (
            <button className="btn-brutal" onClick={login} data-testid="nav-login-btn">
              Sign in
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
