import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Zap, LogOut, LayoutDashboard, Settings, Menu, X } from "lucide-react";

const ROLE_LINKS = {
  admin: [
    { to: "/admin", label: "Command center", icon: LayoutDashboard },
    { to: "/account", label: "My account", icon: Settings },
  ],
};

function SidebarContent({ role, links, locPath, user, onLogout, withClose, onClose }) {
  return (
    <>
      <div className="p-5 border-b border-white/10 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 bg-[#FFD600] border-2 border-white flex items-center justify-center">
            <Zap className="w-5 h-5 text-black" strokeWidth={3} />
          </div>
          <div>
            <div className="font-display text-xl tracking-tighter leading-none">NOSKO</div>
            <div className="overline text-[10px] text-[#FFD600]">{role.toUpperCase()}</div>
          </div>
        </Link>
        {withClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-white p-2 -mr-2"
            data-testid="sidebar-close-btn"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>
      <nav className="flex-1 py-4">
        {links.map((l) => {
          const active = locPath === l.to;
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
        <button onClick={onLogout} className="sidebar-link w-full" data-testid="dashboard-logout-btn">
          <LogOut className="w-4 h-4" /> Sign out
        </button>
      </div>
    </>
  );
}

export default function DashboardLayout({ children, role = "worker" }) {
  const { user, logout } = useAuth();
  const loc = useLocation();
  const [open, setOpen] = useState(false);

  // Close drawer on route change
  useEffect(() => { setOpen(false); }, [loc.pathname]);

  const links = ROLE_LINKS[role] || [];

  return (
    <div className="min-h-screen flex bg-[#F9FAFB]">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-64 bg-[#0A0A0A] text-white flex-col shrink-0">
        <SidebarContent role={role} links={links} locPath={loc.pathname} user={user} onLogout={logout} />
      </aside>

      {/* Mobile slide-out drawer */}
      <div
        className={`lg:hidden fixed inset-0 z-50 ${open ? "" : "pointer-events-none"}`}
        aria-hidden={!open}
      >
        <div
          onClick={() => setOpen(false)}
          className={`absolute inset-0 bg-black/60 transition-opacity ${open ? "opacity-100" : "opacity-0"}`}
        />
        <aside
          className={`absolute left-0 top-0 bottom-0 w-72 max-w-[85vw] bg-[#0A0A0A] text-white flex flex-col transition-transform duration-200 ease-out ${open ? "translate-x-0" : "-translate-x-full"}`}
          data-testid="admin-mobile-sidebar"
        >
          <SidebarContent
            role={role}
            links={links}
            locPath={loc.pathname}
            user={user}
            onLogout={logout}
            withClose
            onClose={() => setOpen(false)}
          />
        </aside>
      </div>

      <main className="flex-1 min-w-0">
        {/* Mobile topbar — only shows below lg */}
        <div className="lg:hidden sticky top-0 z-40 bg-[#0A0A0A] text-white flex items-center justify-between px-4 py-3 border-b-2 border-[#FFD600]">
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 border border-white/20"
            data-testid="admin-menu-btn"
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" /> <span className="overline text-[11px]">Menu</span>
          </button>
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-[#FFD600] flex items-center justify-center">
              <Zap className="w-4 h-4 text-black" strokeWidth={3} />
            </div>
            <span className="font-display text-lg tracking-tighter">NOSKO</span>
          </Link>
          <span className="overline text-[10px] text-[#FFD600]">{role.toUpperCase()}</span>
        </div>
        {children}
      </main>
    </div>
  );
}
