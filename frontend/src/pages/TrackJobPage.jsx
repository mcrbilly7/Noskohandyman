import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, fileUrl } from "@/lib/api";
import Navbar from "@/components/shared/Navbar";
import Footer from "@/components/shared/Footer";
import { CheckCircle2, Clock, Wrench, MapPin, Loader2, AlertTriangle, ArrowRight } from "lucide-react";

const STATUS_META = {
  new: { label: "Received", color: "bg-yellow-200", icon: Clock, step: 1 },
  assigned: { label: "Handyman assigned", color: "bg-blue-200", icon: Wrench, step: 2 },
  in_progress: { label: "In progress", color: "bg-orange-200", icon: Wrench, step: 3 },
  completed: { label: "Completed", color: "bg-green-200", icon: CheckCircle2, step: 4 },
  cancelled: { label: "Cancelled", color: "bg-neutral-200", icon: AlertTriangle, step: 0 },
};

export default function TrackJobPage() {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!jobId) return;
    api.get(`/jobs/track/${jobId}`)
      .then((r) => setJob(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Not found"))
      .finally(() => setLoading(false));
  }, [jobId]);

  if (loading) return (
    <div className="bg-white min-h-screen">
      <Navbar />
      <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 animate-spin" /></div>
    </div>
  );

  if (err) return (
    <div className="bg-white min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-md mx-auto px-6 py-20 text-center">
        <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto" />
        <h1 className="font-display text-3xl mt-3 tracking-tighter">Couldn't find that job</h1>
        <p className="text-neutral-600 mt-2">Double-check the link from your email. If it still doesn't work, email us at <a href="mailto:noskotx@gmail.com" className="underline">noskotx@gmail.com</a>.</p>
        <Link to="/" className="btn-brutal mt-6 inline-flex" data-testid="track-back-home">Back home</Link>
      </main>
      <Footer />
    </div>
  );

  const meta = STATUS_META[job.status] || STATUS_META.new;
  const Icon = meta.icon;

  return (
    <div className="bg-white min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-[1000px] mx-auto px-6 py-12 w-full">
        <div className="overline">Job tracking</div>
        <h1 className="font-display text-4xl md:text-5xl tracking-tighter mt-1" data-testid="track-title">Job <span className="font-mono">{job.job_id}</span></h1>
        <p className="text-neutral-600 mt-2">Hey {job.customer_name?.split(" ")[0]}, here's the live status of your request.</p>

        {/* Big status card */}
        <div className={`mt-8 border-2 border-black ${meta.color} p-8`} data-testid="track-status-card">
          <div className="flex items-center gap-4">
            <Icon className="w-12 h-12" strokeWidth={2.5} />
            <div>
              <div className="overline">Current status</div>
              <div className="font-display text-4xl tracking-tighter">{meta.label}</div>
            </div>
          </div>
          <p className="mt-4 text-sm max-w-prose">{job.eta_message}</p>
        </div>

        {/* Step bar */}
        <div className="grid grid-cols-4 gap-0 border border-black mt-6">
          {["Received", "Assigned", "In progress", "Completed"].map((step, i) => {
            const idx = i + 1;
            const active = idx <= meta.step;
            return (
              <div key={step} className={`p-4 border-r border-black last:border-r-0 ${active ? "bg-[#FFD600]" : "bg-white"}`}>
                <div className="overline">Step {String(idx).padStart(2, "0")}</div>
                <div className="font-display text-sm md:text-base tracking-tight mt-1">{step}</div>
              </div>
            );
          })}
        </div>

        {/* Details */}
        <div className="grid md:grid-cols-2 gap-0 border border-black mt-6">
          <div className="p-6 border-r-0 md:border-r border-black bg-white">
            <div className="overline">Service</div>
            <div className="font-display text-2xl mt-1 tracking-tight">{job.service_type}</div>
            <div className="overline mt-4">Address</div>
            <div className="mt-1 flex items-start gap-2 text-sm">
              <MapPin className="w-4 h-4 mt-0.5 shrink-0" /> {job.address}
            </div>
            {job.assigned_worker_name && (
              <>
                <div className="overline mt-4">Your handyman</div>
                <div className="font-display text-lg mt-1 tracking-tight">{job.assigned_worker_name}</div>
              </>
            )}
          </div>
          <div className="p-6 bg-[#F9FAFB]">
            <div className="overline">Quote</div>
            <div className="font-display text-5xl tracking-tighter mt-1">${job.quoted_amount.toFixed(2)}</div>
            <div className="overline mt-1">Final price · $50 visit minimum applies</div>
            {job.preferred_date && (
              <>
                <div className="overline mt-4">Preferred time</div>
                <div className="text-sm mt-1">{job.preferred_date} · {job.preferred_time_slot}</div>
              </>
            )}
            <div className="overline mt-4">Submitted</div>
            <div className="text-sm">{new Date(job.created_at).toLocaleString()}</div>
          </div>
        </div>

        {/* Photos */}
        {job.photo_paths?.length > 0 && (
          <div className="mt-6">
            <div className="overline">Photos you submitted</div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2">
              {job.photo_paths.map((p, i) => (
                <img key={i} src={fileUrl(p)} alt="" className="w-full aspect-square object-cover border border-black" />
              ))}
            </div>
          </div>
        )}

        <div className="mt-10 flex flex-wrap gap-3">
          <Link to="/request" className="btn-brutal" data-testid="track-new-request-btn">Need another job? <ArrowRight className="w-4 h-4" /></Link>
          <a href="mailto:noskotx@gmail.com" className="btn-brutal ghost" data-testid="track-contact-btn">Contact us</a>
        </div>
      </main>
      <Footer />
    </div>
  );
}
