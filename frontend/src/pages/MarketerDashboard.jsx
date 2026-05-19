import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Copy, Check } from "lucide-react";
import { toast } from "sonner";

export default function MarketerDashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState({ weekly: 0, monthly: 0, yearly: 0, all_time: 0, series: [] });
  const [profile, setProfile] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.get("/earnings/summary").then((r) => setSummary(r.data)).catch(() => {});
    api.get("/marketers/me").then((r) => setProfile(r.data)).catch(() => {});
  }, []);

  const code = profile?.referral_code || user?.referral_code;
  const shareUrl = code ? `${window.location.origin}/request?ref=${code}` : "";

  const copy = () => {
    if (!shareUrl) return;
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    toast.success("Copied!");
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <DashboardLayout role="marketer">
      <div className="p-8 max-w-[1400px]">
        <div className="overline">Marketer dashboard</div>
        <h1 className="font-display text-4xl tracking-tighter mt-1" data-testid="marketer-dashboard-title">Hi, {user?.name?.split(" ")[0]}.</h1>

        <div className="mt-8 grid-box-yellow p-6 border-2 border-black flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="overline">Your referral code</div>
            <div className="font-display text-5xl tracking-tighter font-mono mt-1" data-testid="marketer-code">{code || "—"}</div>
            <div className="overline mt-3">15% profit share on every booking</div>
          </div>
          {code && (
            <div className="flex flex-col gap-2 items-end">
              <div className="font-mono text-sm break-all">{shareUrl}</div>
              <button className="btn-brutal dark" onClick={copy} data-testid="marketer-copy-btn">
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />} Copy link
              </button>
            </div>
          )}
        </div>

        <div className="grid md:grid-cols-4 gap-0 border border-black mt-8">
          {[
            { k: "weekly", l: "This week" },
            { k: "monthly", l: "Last 30 days" },
            { k: "yearly", l: "This year" },
            { k: "all_time", l: "All time" },
          ].map((c, i) => (
            <div key={c.k} className={`p-6 border-r border-black last:border-r-0 ${i === 0 ? "bg-[#FFD600]" : "bg-white"}`}>
              <div className="overline">{c.l}</div>
              <div className="font-display text-4xl tracking-tighter mt-1">${(summary[c.k] || 0).toFixed(2)}</div>
            </div>
          ))}
        </div>

        <div className="mt-8 border border-black bg-white p-6">
          <div className="overline mb-3">Weekly earnings — last 12 weeks</div>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <BarChart data={summary.series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="week" tick={{ fontFamily: "IBM Plex Mono", fontSize: 11 }} />
                <YAxis tick={{ fontFamily: "IBM Plex Mono", fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="amount" fill="#0A0A0A" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
