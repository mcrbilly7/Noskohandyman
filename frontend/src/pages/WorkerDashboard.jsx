import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Briefcase } from "lucide-react";

export default function WorkerDashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState({ weekly: 0, monthly: 0, yearly: 0, all_time: 0, series: [] });
  const [jobs, setJobs] = useState([]);
  const [payouts, setPayouts] = useState([]);

  useEffect(() => {
    api.get("/earnings/summary").then((r) => setSummary(r.data)).catch(() => {});
    api.get("/jobs/me").then((r) => setJobs(r.data || [])).catch(() => {});
    api.get("/payouts/me").then((r) => setPayouts(r.data || [])).catch(() => {});
  }, []);

  return (
    <DashboardLayout role="worker">
      <div className="p-8 max-w-[1400px]">
        <div className="overline">Worker dashboard</div>
        <h1 className="font-display text-4xl tracking-tighter mt-1" data-testid="worker-dashboard-title">Hi, {user?.name?.split(" ")[0]}.</h1>

        <div className="grid md:grid-cols-4 gap-0 border border-black mt-8" data-testid="earnings-cards">
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

        <div className="grid lg:grid-cols-3 gap-0 mt-8 border border-black">
          <div className="lg:col-span-2 p-6 border-r-0 lg:border-r border-black">
            <div className="overline mb-3">Weekly earnings — last 12 weeks</div>
            <div style={{ width: "100%", height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={summary.series}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis dataKey="week" tick={{ fontFamily: "IBM Plex Mono", fontSize: 11 }} />
                  <YAxis tick={{ fontFamily: "IBM Plex Mono", fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="amount" fill="#FFD600" stroke="#0A0A0A" strokeWidth={1.5} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="p-6 bg-white">
            <div className="overline mb-3">Recent payouts</div>
            {payouts.length === 0 ? (
              <p className="text-sm text-neutral-500">No payouts yet.</p>
            ) : (
              <ul className="space-y-3">
                {payouts.slice(0, 8).map((p) => (
                  <li key={p.payout_id} className="flex items-center justify-between border-b border-neutral-200 pb-2">
                    <div>
                      <div className="font-mono text-sm">${p.amount.toFixed(2)}</div>
                      <div className="overline text-[10px]">{new Date(p.created_at).toLocaleDateString()}</div>
                    </div>
                    <span className="overline text-[10px] bg-[#FFD600] border border-black px-2 py-0.5">{p.type}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="mt-8 border border-black bg-white">
          <div className="p-6 border-b border-black flex items-center gap-2">
            <Briefcase className="w-4 h-4" /> <span className="overline">My jobs</span>
          </div>
          {jobs.length === 0 ? (
            <p className="p-6 text-sm text-neutral-500">No jobs assigned yet.</p>
          ) : (
            <table className="w-full text-sm" data-testid="worker-jobs-table">
              <thead className="bg-[#F9FAFB] overline text-[10px]">
                <tr><th className="p-3 text-left">Job</th><th className="p-3 text-left">Service</th><th className="p-3 text-left">Address</th><th className="p-3 text-left">Status</th><th className="p-3 text-left">Qty</th></tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.job_id} className="border-t border-neutral-200">
                    <td className="p-3 font-mono text-xs">{j.job_id}</td>
                    <td className="p-3">{j.service_type}</td>
                    <td className="p-3">{j.address}</td>
                    <td className="p-3"><span className="overline text-[10px] bg-black text-[#FFD600] px-2 py-0.5">{j.status}</span></td>
                    <td className="p-3 font-mono">${j.quoted_amount.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
