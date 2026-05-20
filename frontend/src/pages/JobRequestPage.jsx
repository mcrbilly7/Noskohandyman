import React, { useState } from "react";
import { api } from "@/lib/api";
import Navbar from "@/components/shared/Navbar";
import Footer from "@/components/shared/Footer";
import FileUploader from "@/components/shared/FileUploader";
import { Calendar } from "@/components/ui/calendar";
import { CheckCircle2, Loader2, Clock } from "lucide-react";
import { toast } from "sonner";

const TIME_SLOTS = [
  { id: "morning", label: "Morning", range: "8:00 AM – 12:00 PM" },
  { id: "afternoon", label: "Afternoon", range: "12:00 PM – 5:00 PM" },
  { id: "evening", label: "Evening", range: "5:00 PM – 8:00 PM" },
  { id: "flexible", label: "Flexible", range: "Any time that works" },
];

const SERVICE_OPTIONS = [
  "General Handyman",
  "Electrical (small jobs)",
  "Plumbing",
  "Drywall & paint",
  "Carpentry & install",
  "Tile & flooring",
  "Outdoor & yard",
  "Furniture assembly",
  "Other",
];

function fmtDate(d) {
  if (!d) return "";
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export default function JobRequestPage() {
  const [photos, setPhotos] = useState([]);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);
  const [date, setDate] = useState(null);
  const [slot, setSlot] = useState("flexible");
  const [form, setForm] = useState({
    customer_name: "",
    customer_email: "",
    customer_phone: "",
    address: "",
    service_type: "General Handyman",
    description: "",
  });

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await api.post("/jobs", {
        ...form,
        photo_paths: photos,
        preferred_date: fmtDate(date) || null,
        preferred_time_slot: slot,
      });
      setDone(res.data);
      toast.success("Quote request sent!");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not submit");
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    const trackUrl = `${window.location.origin}/track/${done.job_id}`;
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
            {done.preferred_date && (
              <p className="text-neutral-700 mt-2 inline-flex items-center gap-2">
                <Clock className="w-4 h-4" /> Preferred: <b>{done.preferred_date}</b> · {TIME_SLOTS.find(t => t.id === done.preferred_time_slot)?.label || done.preferred_time_slot}
              </p>
            )}
            <div className="mt-8 border-2 border-black bg-[#FFD600] p-5" data-testid="job-track-link-block">
              <div className="overline">Track your job anytime — no login</div>
              <div className="font-mono text-sm break-all mt-1">{trackUrl}</div>
              <a href={trackUrl} className="btn-brutal dark mt-3 inline-flex" data-testid="job-track-btn">Open tracking page</a>
            </div>
            <div className="flex flex-wrap gap-2 mt-6">
              <a href="/" className="btn-brutal ghost" data-testid="request-success-home">Back home</a>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const today = new Date(); today.setHours(0, 0, 0, 0);

  return (
    <div className="bg-white min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-[1200px] mx-auto px-6 py-12 w-full grid lg:grid-cols-3 gap-0 border border-black">
        <div className="lg:col-span-2 p-8 border-r-0 lg:border-r border-black">
          <div className="overline">Request a quote</div>
          <h1 className="font-display text-4xl mt-2 tracking-tighter">Tell us what's broken.</h1>
          <p className="text-neutral-600 mt-2">Photo + a few details + pick a time. We'll send a quote.</p>

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
                  {SERVICE_OPTIONS.map((o) => <option key={o}>{o}</option>)}
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

            {/* Scheduling */}
            <div className="border-2 border-black p-5 mt-2" data-testid="job-schedule-block">
              <div className="overline">Preferred time</div>
              <div className="font-display text-xl tracking-tight mt-1">Pick a day & window</div>
              <p className="text-sm text-neutral-600 mt-1">Helps us batch nearby jobs in one trip. Not binding — we'll confirm.</p>

              <div className="grid md:grid-cols-2 gap-6 mt-4">
                <div className="border border-black bg-white">
                  <Calendar
                    mode="single"
                    selected={date}
                    onSelect={setDate}
                    disabled={(d) => d < today}
                    data-testid="job-calendar"
                  />
                </div>
                <div>
                  <div className="overline mb-2">Time window</div>
                  <div className="grid gap-2">
                    {TIME_SLOTS.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setSlot(t.id)}
                        className={`text-left border-2 border-black p-3 ${slot === t.id ? "bg-[#FFD600]" : "bg-white hover:bg-neutral-50"}`}
                        data-testid={`job-slot-${t.id}`}
                      >
                        <div className="font-display text-lg tracking-tight">{t.label}</div>
                        <div className="overline text-[10px] text-neutral-600">{t.range}</div>
                      </button>
                    ))}
                  </div>
                  {date && (
                    <div className="mt-3 text-sm" data-testid="job-schedule-summary">
                      <span className="overline">Selected:</span>{" "}
                      <b>{date.toDateString()}</b>{" "}
                      · {TIME_SLOTS.find(t => t.id === slot)?.label}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <button type="submit" className="btn-brutal dark mt-2" disabled={busy} data-testid="job-submit-btn">
              {busy ? <><Loader2 className="w-4 h-4 animate-spin" /> Sending…</> : "Send request"}
            </button>
          </form>
        </div>

        <aside className="p-8 bg-[#FFD600] border-t lg:border-t-0 border-black">
          <div className="overline">Visit minimum</div>
          <div className="font-display text-7xl tracking-tighter mt-1">$50</div>
          <p className="text-sm mt-2">Every visit has a $50 floor — covers travel + diagnosis.</p>
          <div className="mt-6 border-t border-black pt-4">
            <div className="overline">All other work</div>
            <div className="font-display text-2xl tracking-tight">Free written quote</div>
            <p className="text-sm mt-2">Fixed-price. No upcharge games.</p>
          </div>
          <div className="mt-8 border-t border-black pt-4">
            <div className="overline">What you get</div>
            <ul className="mt-2 space-y-1 text-sm">
              <li>· Real W9-compliant handyman</li>
              <li>· Photo confirmation</li>
              <li>· Time-window scheduling</li>
              <li>· Quote within 24 hrs</li>
            </ul>
          </div>
        </aside>
      </main>
      <Footer />
    </div>
  );
}
