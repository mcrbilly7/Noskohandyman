import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import Navbar from "@/components/shared/Navbar";
import Footer from "@/components/shared/Footer";
import W9Signer from "@/components/shared/W9Signer";
import { Wrench, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

const SKILL_OPTIONS = ["Electrical", "Plumbing", "Carpentry", "Drywall", "Painting", "Appliance install", "General handyman"];

export default function WorkerSignupPage() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1 = profile, 2 = W9, 3 = done
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    hours_per_week: 20,
    skills: [],
    location: "",
    phone: "",
    bio: "",
  });

  useEffect(() => {
    if (!loading && !user) return;
    if (user) {
      api.get("/w9/me").then((r) => {
        if (r.data?.signed_at) setStep(3);
      }).catch(() => {});
    }
  }, [user, loading]);

  const toggleSkill = (s) => {
    setForm((f) => ({
      ...f,
      skills: f.skills.includes(s) ? f.skills.filter((x) => x !== s) : [...f.skills, s],
    }));
  };

  const submitProfile = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/workers/signup", form);
      toast.success("Profile saved");
      setStep(2);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const submitW9 = async (data) => {
    setBusy(true);
    try {
      await api.post("/w9/sign", data);
      toast.success("W9 signed");
      setStep(3);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally {
      setBusy(false);
    }
  };

  if (!loading && !user) {
    return (
      <div className="bg-white min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-[900px] mx-auto px-6 py-20">
          <div className="overline">Handyman application</div>
          <h1 className="font-display text-5xl mt-2 tracking-tighter">Sign in to start.</h1>
          <p className="text-neutral-700 mt-3 max-w-lg">
            We use Google sign-in. After signing in, you'll set your hours, skills, location and sign your W9.
          </p>
          <button className="btn-brutal mt-8" onClick={login} data-testid="worker-signin-btn">Sign in with Google</button>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="bg-white min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-[1100px] mx-auto px-6 py-12 w-full">
        <div className="overline">Become a handyman</div>
        <h1 className="font-display text-5xl mt-2 tracking-tighter">Apply.</h1>

        {/* Steps */}
        <div className="grid grid-cols-3 gap-0 mt-8 border border-black">
          {["Profile", "Sign W9", "Done"].map((label, i) => (
            <div key={label} className={`p-4 border-r border-black last:border-r-0 ${step === i + 1 ? "bg-[#FFD600]" : ""}`}>
              <div className="overline">Step {String(i + 1).padStart(2, "0")}</div>
              <div className="font-display text-xl tracking-tighter">{label}</div>
            </div>
          ))}
        </div>

        {step === 1 && (
          <form onSubmit={submitProfile} className="mt-10 grid gap-4 border-2 border-black p-8" data-testid="worker-profile-form">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="overline">Hours / week</label>
                <input type="number" min="1" max="80" value={form.hours_per_week} onChange={(e) => setForm({ ...form, hours_per_week: parseInt(e.target.value || "0") })} data-testid="worker-hours" />
              </div>
              <div>
                <label className="overline">Location (city, state)</label>
                <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} required data-testid="worker-location" />
              </div>
            </div>
            <div>
              <label className="overline">Phone</label>
              <input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="worker-phone" />
            </div>
            <div>
              <label className="overline">Skills</label>
              <div className="flex flex-wrap gap-2 mt-2">
                {SKILL_OPTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleSkill(s)}
                    className={`px-3 py-1.5 border-2 border-black overline ${form.skills.includes(s) ? "bg-[#FFD600]" : "bg-white"}`}
                    data-testid={`worker-skill-${s}`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="overline">Short bio</label>
              <textarea rows={3} value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} data-testid="worker-bio" />
            </div>
            <button className="btn-brutal dark" disabled={busy} data-testid="worker-profile-submit">
              {busy ? "Saving…" : "Save & continue to W9"}
            </button>
          </form>
        )}

        {step === 2 && (
          <div className="mt-10 border-2 border-black p-8">
            <div className="overline mb-4">IRS W9 — substitute form</div>
            <W9Signer onSubmit={submitW9} busy={busy} />
          </div>
        )}

        {step === 3 && (
          <div className="mt-10 border-2 border-black p-10 text-center bg-[#F9FAFB]">
            <CheckCircle2 className="w-12 h-12 text-[#16A34A] mx-auto" />
            <h2 className="font-display text-3xl mt-3 tracking-tighter">You're in.</h2>
            <p className="text-neutral-700 mt-2">
              Head to your dashboard to see assigned jobs and earnings.
            </p>
            <button className="btn-brutal mt-6" onClick={() => navigate("/dashboard/worker")} data-testid="worker-goto-dashboard">
              <Wrench className="w-4 h-4" /> Go to dashboard
            </button>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
