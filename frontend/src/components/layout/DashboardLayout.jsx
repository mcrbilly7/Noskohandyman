import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Zap, LogOut, LayoutDashboard, Settings } from "lucide-react";

export default function DashboardLayout({ children, role = "worker" }) {
  const { user, logout } = useAuth();
  const loc = useLocation();
  const nav = useNavigate();

  const links = {
    admin: [
      { to: "/admin", label: "Command center", icon: LayoutDashboard },
      { to: "/account", label: "My account", icon: Settings },
    ],
  }[role] || [];

  return (
    <div className="min-h-screen flex bg-[#F9FAFB]">
      <aside className="w-64 bg-[#0A0A0A] text-white flex flex-col">
        <div className="p-6 border-b border-white/10">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-9 h-9 bg-[#FFD600] border-2 border-white flex items-center justify-center">
              <Zap className="w-5 h-5 text-black" strokeWidth={3} />
            </div>
            <div>
              <div className="font-display text-xl tracking-tighter leading-none">NOSKO</div>
              <div className="overline text-[10px] text-[#FFD600]">{role.toUpperCase()}</div>
            </div>
          </Link>
        </div>
        <nav className="flex-1 py-4">
          {links.map((l) => {
            const active = loc.pathname === l.to;
            return (
              <Link key={l.to} to={l.to} className={`sidebar-link ${active ? "active" : ""}`} data-testid={`sidebar-${l.label.toLowerCase().replace(/\s+/g, "-")}`}>
                <l.icon className="w-4 h-4" /> {l.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-white/10">
          {user && (
            <div className="mb-3">
              <div className="overline text-[#FFD600] text-[10px]">Signed in</div>
              <div className="font-mono text-sm truncate">{user.email}</div>
            </div>
          )}
          <button onClick={logout} className="sidebar-link w-full" data-testid="dashboard-logout-btn">
            <LogOut className="w-4 h-4" /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-x-hidden">
        {children}
      </main>
    </div>
  );
}
