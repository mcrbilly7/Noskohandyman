import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import Navbar from "@/components/shared/Navbar";
import Footer from "@/components/shared/Footer";
import FileUploader from "@/components/shared/FileUploader";
import { CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function JobRequestPage() {
  const [params] = useSearchParams();
  const [photos, setPhotos] = useState([]);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);
  const [refStatus, setRefStatus] = useState(null);
  const [form, setForm] = useState({
    customer_name: "",
    customer_email: "",
    customer_phone: "",
    address: "",
    service_type: "Switch/Outlet Replacement",
    description: "",
    referral_code: (params.get("ref") || "").toUpperCase(),
  });

  useEffect(() => {
    if (!form.referral_code) { setRefStatus(null); return; }
    const t = setTimeout(async () => {
      try {
        const r = await api.get(`/referral/${form.referral_code}`);
        setRefStatus(r.data);
      } catch { setRefStatus({ valid: false }); }
    }, 300);
    return () => clearTimeout(t);
  }, [form.referral_code]);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await api.post("/jobs", { ...form, photo_paths: photos });
      setDone(res.data);
      toast.success("Job request sent!");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not submit");
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <div className="bg-white min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-[900px] mx-auto px-6 py-20 w-full">
          <div className="border-2 border-black p-10 fade-in">
            <CheckCircle2 className="w-12 h-12 text-[#16A34A]" />
            <h1 className="font-display text-4xl mt-4 tracking-tighter">Request received.</h1>
            <p className="text-neutral-700 mt-3">
              Job <span className="font-mono">{done.job_id}</span> is in the queue. We'll be in touch at <b>{done.customer_email}</b>.
            </p>
            <div className="overline mt-6">Quoted</div>
            <div className="font-display text-5xl">${done.quoted_amount.toFixed(2)}</div>
            <a href="/" className="btn-brutal mt-8 inline-flex" data-testid="request-success-home">Back home</a>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="bg-white min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-[1200px] mx-auto px-6 py-12 w-full grid lg:grid-cols-3 gap-0 border border-black">
        <div className="lg:col-span-2 p-8 border-r-0 lg:border-r border-black">
          <div className="overline">Request a job</div>
          <h1 className="font-display text-4xl mt-2 tracking-tighter">Tell us what's broken.</h1>
          <p className="text-neutral-600 mt-2">Photo + a few details. We'll dispatch a handyman.</p>

          <form onSubmit={submit} className="grid gap-4 mt-8" data-testid="job-request-form">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="overline">Your name *</label>
                <input required value={form.customer_name} onChange={set("customer_name")} data-testid="job-name" />
              </div>
              <div>
                <label className="overline">Email *</label>
                <input type="email" required value={form.customer_email} onChange={set("customer_email")} data-testid="job-email" />
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="overline">Phone</label>
                <input type="tel" value={form.customer_phone} onChange={set("customer_phone")} data-testid="job-phone" />
              </div>
              <div>
                <label className="overline">Service *</label>
                <select value={form.service_type} onChange={set("service_type")} data-testid="job-service">
                  <option>Switch/Outlet Replacement</option>
                  <option>General Handyman</option>
                  <option>Other</option>
                </select>
              </div>
            </div>
            <div>
              <label className="overline">Address *</label>
              <input required value={form.address} onChange={set("address")} data-testid="job-address" />
            </div>
            <div>
              <label className="overline">What's the issue? *</label>
              <textarea required rows={4} value={form.description} onChange={set("description")} data-testid="job-description" />
            </div>
            <div>
              <label className="overline">Photo of the job *</label>
              <FileUploader folder="jobs" value={photos} onChange={setPhotos} testid="job-photos" />
            </div>
            <div>
              <label className="overline">Referral code (optional)</label>
              <input
                value={form.referral_code}
                onChange={(e) => setForm({ ...form, referral_code: e.target.value.toUpperCase() })}
                placeholder="e.g. JOHN-A1B2"
                data-testid="job-referral"
              />
              {refStatus?.valid && (
                <div className="text-[#16A34A] text-sm mt-1">✓ Referral by {refStatus.marketer_name}</div>
              )}
              {refStatus?.valid === false && form.referral_code && (
                <div className="text-red-600 text-sm mt-1">Invalid code</div>
              )}
            </div>
            <button type="submit" className="btn-brutal dark" disabled={busy} data-testid="job-submit-btn">
              {busy ? <><Loader2 className="w-4 h-4 animate-spin" /> Sending…</> : "Send request"}
            </button>
          </form>
        </div>

        <aside className="p-8 bg-[#FFD600] border-t lg:border-t-0 border-black">
          <div className="overline">Per swap</div>
          <div className="font-display text-7xl tracking-tighter mt-1">$25</div>
          <div className="overline">Switch / outlet replacement</div>
          <div className="mt-6 border-t border-black pt-4">
            <div className="overline">Visit minimum</div>
            <div className="font-display text-5xl tracking-tighter">$50</div>
            <p className="text-sm mt-2">Every visit has a $50 floor — covers travel + diagnosis.</p>
          </div>
          <div className="mt-8 border-t border-black pt-4">
            <div className="overline">What you get</div>
            <ul className="mt-2 space-y-1 text-sm">
              <li>· Real W9-compliant handyman</li>
              <li>· Photo confirmation</li>
              <li>· Fixed-price quote</li>
              <li>· No upcharge games</li>
            </ul>
          </div>
        </aside>
      </main>
      <Footer />
    </div>
  );
}
