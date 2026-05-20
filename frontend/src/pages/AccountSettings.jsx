import React, { useEffect, useState } from "react";
import { useAuth, formatApiError } from "@/lib/auth";
import { api } from "@/lib/api";
import Navbar from "@/components/shared/Navbar";
import Footer from "@/components/shared/Footer";
import { Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Link } from "react-router-dom";

export default function AccountSettings() {
  const { user, refresh } = useAuth();
  const [form, setForm] = useState({ name: "", phone: "", location: "", notify_email: true });
  const [pw, setPw] = useState({ password: "", password2: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) setForm({
      name: user.name || "",
      phone: user.phone || "",
      location: user.location || "",
      notify_email: user.notify_email !== false,
    });
  }, [user]);

  const saveProfile = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.put("/users/me", form);
      await refresh();
      toast.success("Saved");
    } catch (e2) { toast.error(formatApiError(e2)); }
    finally { setBusy(false); }
  };

  const savePassword = async (e) => {
    e.preventDefault();
    if (pw.password !== pw.password2) { toast.error("Passwords don't match"); return; }
    if (pw.password.length < 8) { toast.error("Min 8 characters"); return; }
    setBusy(true);
    try {
      await api.put("/users/me", { password: pw.password });
      setPw({ password: "", password2: "" });
      toast.success("Password updated");
    } catch (e2) { toast.error(formatApiError(e2)); }
    finally { setBusy(false); }
  };

  if (!user) return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin" />
    </div>
  );

  return (
    <div className="bg-white min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-[1100px] mx-auto px-6 py-12 w-full">
        <div className="overline">Account</div>
        <h1 className="font-display text-4xl tracking-tighter mt-1" data-testid="account-title">Settings</h1>

        <div className="grid md:grid-cols-3 gap-0 border border-black mt-6">
          <div className="p-5 border-r border-black bg-[#F9FAFB]">
            <div className="overline">Signed in as</div>
            <div className="font-display text-xl tracking-tighter truncate" data-testid="account-email">{user.email}</div>
          </div>
          <div className="p-5 border-r border-black">
            <div className="overline">Role</div>
            <div className="font-display text-xl tracking-tighter capitalize">{user.role}</div>
          </div>
          <div className="p-5 bg-[#FFD600]">
            <div className="overline">Quick links</div>
            <div className="flex flex-wrap gap-2 mt-2">
              {(user.role === "admin" || user.role === "developer") && <Link to="/admin" className="overline border border-black px-2 py-1" data-testid="account-admin-link"><ShieldCheck className="w-3 h-3 inline mr-1" />Admin</Link>}
              <Link to="/request" className="overline border border-black px-2 py-1" data-testid="account-quote-link">Get a quote</Link>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-8 mt-10">
          <form onSubmit={saveProfile} className="border-2 border-black p-6 grid gap-3" data-testid="account-profile-form">
            <div className="overline">Profile</div>
            <div>
              <label className="overline">Name</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="account-name" />
            </div>
            <div>
              <label className="overline">Phone</label>
              <input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="account-phone" />
            </div>
            <div>
              <label className="overline">Location</label>
              <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} data-testid="account-location" />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="!w-auto" checked={form.notify_email} onChange={(e) => setForm({ ...form, notify_email: e.target.checked })} data-testid="account-notify" />
              Email me updates
            </label>
            <button className="btn-brutal dark mt-2" disabled={busy} data-testid="account-save-btn">Save profile</button>
          </form>

          <form onSubmit={savePassword} className="border-2 border-black p-6 grid gap-3" data-testid="account-password-form">
            <div className="overline">Change password</div>
            {user.auth_provider === "google" && !user.password_hash && (
              <p className="text-sm text-neutral-600">You signed in with Google. Setting a password here lets you also sign in with email + password.</p>
            )}
            <div>
              <label className="overline">New password</label>
              <input type="password" minLength={8} value={pw.password} onChange={(e) => setPw({ ...pw, password: e.target.value })} data-testid="account-pw" />
            </div>
            <div>
              <label className="overline">Confirm</label>
              <input type="password" minLength={8} value={pw.password2} onChange={(e) => setPw({ ...pw, password2: e.target.value })} data-testid="account-pw2" />
            </div>
            <button className="btn-brutal mt-2" disabled={busy} data-testid="account-password-btn">Update password</button>
          </form>
        </div>
      </main>
      <Footer />
    </div>
  );
}
