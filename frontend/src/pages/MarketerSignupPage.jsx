import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import Navbar from "@/components/shared/Navbar";
import Footer from "@/components/shared/Footer";
import W9Signer from "@/components/shared/W9Signer";
import { BadgeDollarSign, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

export default function MarketerSignupPage() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [code, setCode] = useState(null);
  const [form, setForm] = useState({ phone: "", location: "" });

  useEffect(() => {
    if (!user) return;
    api.get("/marketers/me").then((r) => {
      if (r.data?.referral_code) setCode(r.data.referral_code);
    }).catch(() => {});
    api.get("/w9/me").then((r) => { if (r.data?.signed_at && code) setStep(3); }).catch(() => {});
  }, [user, code]);

  const submitProfile = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await api.post("/marketers/signup", form);
      setCode(res.data.referral_code);
      toast.success("Profile saved");
      setStep(2);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally { setBusy(false); }
  };

  const submitW9 = async (data) => {
    setBusy(true);
    try {
      await api.post("/w9/sign", data);
      toast.success("W9 signed");
      setStep(3);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally { setBusy(false); }
  };

  if (!loading && !user) {
    return (
      <div className="bg-white min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-[900px] mx-auto px-6 py-20">
          <div className="overline">Marketer program</div>
          <h1 className="font-display text-5xl mt-2 tracking-tighter">15% profit share.</h1>
          <p className="text-neutral-700 mt-3 max-w-lg">
            Share your personal code. Anyone who books with it earns you 15% — paid weekly. Sign in to get your code.
          </p>
          <button className="btn-brutal mt-8" onClick={login} data-testid="marketer-signin-btn">Sign in with Google</button>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="bg-white min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-[1100px] mx-auto px-6 py-12 w-full">
        <div className="overline">Marketer program</div>
        <h1 className="font-display text-5xl mt-2 tracking-tighter">Get your code.</h1>

        <div className="grid grid-cols-3 gap-0 mt-8 border border-black">
          {["Profile", "Sign W9", "Done"].map((label, i) => (
            <div key={label} className={`p-4 border-r border-black last:border-r-0 ${step === i + 1 ? "bg-[#FFD600]" : ""}`}>
              <div className="overline">Step {String(i + 1).padStart(2, "0")}</div>
              <div className="font-display text-xl tracking-tighter">{label}</div>
            </div>
          ))}
        </div>

        {step === 1 && (
          <form onSubmit={submitProfile} className="mt-10 grid gap-4 border-2 border-black p-8" data-testid="marketer-profile-form">
            <div>
              <label className="overline">Phone</label>
              <input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="marketer-phone" />
            </div>
            <div>
              <label className="overline">Location</label>
              <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} data-testid="marketer-location" />
            </div>
            <button className="btn-brutal dark" disabled={busy} data-testid="marketer-profile-submit">
              {busy ? "Saving…" : "Get my code"}
            </button>
          </form>
        )}

        {step === 2 && (
          <>
            {code && (
              <div className="mt-10 grid-box-yellow p-8 border-2 border-black" data-testid="marketer-code-block">
                <div className="overline">Your referral code</div>
                <div className="font-display text-5xl tracking-tighter mt-2 font-mono">{code}</div>
                <p className="text-sm mt-2">Share <code className="font-mono">/request?ref={code}</code> with anyone you refer.</p>
              </div>
            )}
            <div className="mt-8 border-2 border-black p-8">
              <div className="overline mb-4">IRS W9 — substitute form</div>
              <W9Signer onSubmit={submitW9} busy={busy} />
            </div>
          </>
        )}

        {step === 3 && (
          <div className="mt-10 border-2 border-black p-10 text-center bg-[#F9FAFB]">
            <CheckCircle2 className="w-12 h-12 text-[#16A34A] mx-auto" />
            <h2 className="font-display text-3xl mt-3 tracking-tighter">You're live.</h2>
            <p className="text-neutral-700 mt-2">Share your code and watch your dashboard.</p>
            <button className="btn-brutal mt-6" onClick={() => navigate("/dashboard/marketer")} data-testid="marketer-goto-dashboard">
              <BadgeDollarSign className="w-4 h-4" /> Go to dashboard
            </button>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
