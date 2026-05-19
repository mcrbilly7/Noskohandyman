import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api, fileUrl } from "@/lib/api";
import DashboardLayout from "@/components/layout/DashboardLayout";
import FileUploader from "@/components/shared/FileUploader";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Image as ImageIcon, Trash2, Send, DollarSign } from "lucide-react";
import { toast } from "sonner";

export default function AdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState({});
  const [jobs, setJobs] = useState([]);
  const [workers, setWorkers] = useState([]);
  const [marketers, setMarketers] = useState([]);
  const [portfolio, setPortfolio] = useState([]);
  const [settings, setSettings] = useState({});

  const refreshAll = () => {
    api.get("/admin/stats").then((r) => setStats(r.data)).catch(() => {});
    api.get("/jobs").then((r) => setJobs(r.data || [])).catch(() => {});
    api.get("/workers").then((r) => setWorkers(r.data || [])).catch(() => {});
    api.get("/marketers").then((r) => setMarketers(r.data || [])).catch(() => {});
    api.get("/portfolio").then((r) => setPortfolio(r.data || [])).catch(() => {});
    api.get("/site/settings").then((r) => setSettings(r.data)).catch(() => {});
  };

  useEffect(() => { refreshAll(); }, []);

  const assignWorker = async (jobId, workerId) => {
    if (!workerId) return;
    try {
      await api.put(`/jobs/${jobId}/assign`, { worker_id: workerId });
      toast.success("Assigned");
      refreshAll();
    } catch (e) { toast.error("Assign failed"); }
  };

  const setStatus = async (jobId, status) => {
    try {
      await api.put(`/jobs/${jobId}/status`, { status });
      toast.success("Updated");
      refreshAll();
    } catch (e) { toast.error("Update failed"); }
  };

  const payUser = async (userId, type) => {
    const amt = prompt("Amount to pay (USD):");
    if (!amt) return;
    const note = prompt("Note (optional):") || "";
    try {
      await api.post("/payouts", { user_id: userId, amount: parseFloat(amt), type, note, method: "stripe" });
      toast.success("Payout recorded");
      refreshAll();
    } catch (e) { toast.error("Payout failed"); }
  };

  return (
    <DashboardLayout role="admin">
      <div className="p-8 max-w-[1400px]">
        <div className="overline">Admin</div>
        <h1 className="font-display text-4xl tracking-tighter mt-1" data-testid="admin-title">Command center</h1>

        <div className="grid md:grid-cols-5 gap-0 border border-black mt-6" data-testid="admin-stats">
          {[
            { l: "New jobs", v: stats.jobs_new || 0, hl: true },
            { l: "Total jobs", v: stats.jobs_total || 0 },
            { l: "Completed", v: stats.jobs_completed || 0 },
            { l: "Workers", v: stats.workers || 0 },
            { l: "Marketers", v: stats.marketers || 0 },
          ].map((c) => (
            <div key={c.l} className={`p-5 border-r border-black last:border-r-0 ${c.hl ? "bg-[#FFD600]" : "bg-white"}`}>
              <div className="overline">{c.l}</div>
              <div className="font-display text-4xl tracking-tighter mt-1">{c.v}</div>
            </div>
          ))}
        </div>

        <Tabs defaultValue="jobs" className="mt-8">
          <TabsList className="bg-black text-white rounded-none border-2 border-black p-0 h-auto">
            <TabsTrigger value="jobs" className="rounded-none data-[state=active]:bg-[#FFD600] data-[state=active]:text-black overline px-4 py-2" data-testid="tab-jobs">Jobs</TabsTrigger>
            <TabsTrigger value="workers" className="rounded-none data-[state=active]:bg-[#FFD600] data-[state=active]:text-black overline px-4 py-2" data-testid="tab-workers">Workers</TabsTrigger>
            <TabsTrigger value="marketers" className="rounded-none data-[state=active]:bg-[#FFD600] data-[state=active]:text-black overline px-4 py-2" data-testid="tab-marketers">Marketers</TabsTrigger>
            <TabsTrigger value="portfolio" className="rounded-none data-[state=active]:bg-[#FFD600] data-[state=active]:text-black overline px-4 py-2" data-testid="tab-portfolio">Portfolio</TabsTrigger>
            <TabsTrigger value="settings" className="rounded-none data-[state=active]:bg-[#FFD600] data-[state=active]:text-black overline px-4 py-2" data-testid="tab-settings">Settings</TabsTrigger>
          </TabsList>

          {/* JOBS */}
          <TabsContent value="jobs" className="mt-4">
            <div className="border-2 border-black bg-white" data-testid="admin-jobs-section">
              {jobs.length === 0 ? <p className="p-6 text-sm text-neutral-500">No job requests yet.</p> : (
                <div className="divide-y divide-black/10">
                  {jobs.map((j) => (
                    <div key={j.job_id} className="p-5 grid lg:grid-cols-12 gap-4">
                      <div className="lg:col-span-2 flex gap-2 flex-wrap">
                        {(j.photo_paths || []).slice(0, 4).map((p, idx) => (
                          <img key={idx} src={fileUrl(p)} alt="" className="w-20 h-20 object-cover border border-black" />
                        ))}
                        {(j.photo_paths || []).length === 0 && <div className="w-20 h-20 border border-black bg-neutral-100 flex items-center justify-center text-xs">no img</div>}
                      </div>
                      <div className="lg:col-span-5">
                        <div className="overline">{j.service_type}</div>
                        <div className="font-display text-xl tracking-tighter">{j.customer_name}</div>
                        <div className="text-sm text-neutral-600">{j.customer_email} · {j.customer_phone || "—"}</div>
                        <div className="text-sm mt-1">{j.address}</div>
                        <p className="text-sm mt-2 max-w-prose">{j.description}</p>
                        {j.referral_code && <span className="overline text-[10px] inline-block mt-2 bg-[#FFD600] border border-black px-2 py-0.5">ref · {j.referral_code}</span>}
                      </div>
                      <div className="lg:col-span-3">
                        <div className="overline">Assign worker</div>
                        <select className="mt-1" onChange={(e) => assignWorker(j.job_id, e.target.value)} value={j.assigned_worker_id || ""} data-testid={`assign-${j.job_id}`}>
                          <option value="">{j.assigned_worker_id ? "Change…" : "Select worker"}</option>
                          {workers.map((w) => (
                            <option key={w.user_id} value={w.user_id}>{w.user?.name || w.user?.email} — {w.location || "n/a"}</option>
                          ))}
                        </select>
                        <select className="mt-2" onChange={(e) => setStatus(j.job_id, e.target.value)} value={j.status} data-testid={`status-${j.job_id}`}>
                          <option value="new">new</option>
                          <option value="assigned">assigned</option>
                          <option value="in_progress">in_progress</option>
                          <option value="completed">completed</option>
                          <option value="cancelled">cancelled</option>
                        </select>
                      </div>
                      <div className="lg:col-span-2 text-right">
                        <div className="overline">Quote</div>
                        <div className="font-display text-3xl tracking-tighter">${j.quoted_amount.toFixed(2)}</div>
                        <div className="overline text-[10px] bg-black text-[#FFD600] inline-block px-2 py-0.5 mt-1">{j.status}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          {/* WORKERS */}
          <TabsContent value="workers" className="mt-4">
            <div className="border-2 border-black bg-white" data-testid="admin-workers-section">
              {workers.length === 0 ? <p className="p-6 text-sm text-neutral-500">No workers yet.</p> : (
                <table className="w-full text-sm">
                  <thead className="bg-[#F9FAFB] overline text-[10px]">
                    <tr><th className="p-3 text-left">Worker</th><th className="p-3 text-left">Skills</th><th className="p-3 text-left">Location</th><th className="p-3 text-left">Hrs/wk</th><th className="p-3 text-right">Action</th></tr>
                  </thead>
                  <tbody>
                    {workers.map((w) => (
                      <tr key={w.user_id} className="border-t border-neutral-200">
                        <td className="p-3">
                          <div className="font-display tracking-tight">{w.user?.name}</div>
                          <div className="font-mono text-xs text-neutral-500">{w.user?.email}</div>
                        </td>
                        <td className="p-3 text-xs">{(w.skills || []).join(", ")}</td>
                        <td className="p-3">{w.location || "—"}</td>
                        <td className="p-3 font-mono">{w.hours_per_week || "—"}</td>
                        <td className="p-3 text-right">
                          <button className="btn-brutal" onClick={() => payUser(w.user_id, "work")} data-testid={`pay-worker-${w.user_id}`}>
                            <DollarSign className="w-4 h-4" /> Pay
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </TabsContent>

          {/* MARKETERS */}
          <TabsContent value="marketers" className="mt-4">
            <div className="border-2 border-black bg-white" data-testid="admin-marketers-section">
              {marketers.length === 0 ? <p className="p-6 text-sm text-neutral-500">No marketers yet.</p> : (
                <table className="w-full text-sm">
                  <thead className="bg-[#F9FAFB] overline text-[10px]">
                    <tr><th className="p-3 text-left">Marketer</th><th className="p-3 text-left">Code</th><th className="p-3 text-left">Location</th><th className="p-3 text-left">Referrals</th><th className="p-3 text-right">Action</th></tr>
                  </thead>
                  <tbody>
                    {marketers.map((m) => (
                      <tr key={m.user_id} className="border-t border-neutral-200">
                        <td className="p-3">
                          <div className="font-display tracking-tight">{m.user?.name}</div>
                          <div className="font-mono text-xs text-neutral-500">{m.user?.email}</div>
                        </td>
                        <td className="p-3 font-mono">{m.referral_code}</td>
                        <td className="p-3">{m.location || "—"}</td>
                        <td className="p-3 font-mono">{m.referral_count}</td>
                        <td className="p-3 text-right">
                          <button className="btn-brutal" onClick={() => payUser(m.user_id, "referral")} data-testid={`pay-marketer-${m.user_id}`}>
                            <Send className="w-4 h-4" /> Pay
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </TabsContent>

          {/* PORTFOLIO */}
          <TabsContent value="portfolio" className="mt-4">
            <PortfolioEditor portfolio={portfolio} refresh={refreshAll} />
          </TabsContent>

          {/* SETTINGS */}
          <TabsContent value="settings" className="mt-4">
            <SiteSettingsEditor settings={settings} onSave={refreshAll} />
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}

function PortfolioEditor({ portfolio, refresh }) {
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [paths, setPaths] = useState([]);

  const add = async (e) => {
    e.preventDefault();
    if (!title || paths.length === 0) { toast.error("Title + photo required"); return; }
    try {
      for (const p of paths) {
        await api.post("/portfolio", { title, description: desc, storage_path: p });
      }
      toast.success("Added");
      setTitle(""); setDesc(""); setPaths([]);
      refresh();
    } catch { toast.error("Failed"); }
  };

  const remove = async (id) => {
    if (!confirm("Delete?")) return;
    try { await api.delete(`/portfolio/${id}`); refresh(); } catch { toast.error("Failed"); }
  };

  return (
    <div className="grid lg:grid-cols-3 gap-0 border-2 border-black" data-testid="admin-portfolio-section">
      <form onSubmit={add} className="p-6 border-r border-black bg-[#F9FAFB] grid gap-3">
        <div className="overline">Upload work photos</div>
        <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} data-testid="portfolio-title" />
        <textarea placeholder="Description (optional)" rows={2} value={desc} onChange={(e) => setDesc(e.target.value)} data-testid="portfolio-desc" />
        <FileUploader folder="portfolio" value={paths} onChange={setPaths} testid="portfolio-uploader" />
        <button className="btn-brutal dark" data-testid="portfolio-submit-btn"><ImageIcon className="w-4 h-4" /> Add to portfolio</button>
      </form>
      <div className="lg:col-span-2 p-6 grid grid-cols-2 md:grid-cols-3 gap-3">
        {portfolio.length === 0 ? <div className="text-sm text-neutral-500 col-span-full">No photos yet.</div> :
          portfolio.map((p) => (
            <div key={p.photo_id} className="border border-black relative">
              <img src={fileUrl(p.storage_path)} alt={p.title} className="w-full aspect-square object-cover" />
              <div className="p-2 overline text-[10px]">{p.title}</div>
              <button onClick={() => remove(p.photo_id)} className="absolute top-1 right-1 bg-black text-white p-1" data-testid={`portfolio-delete-${p.photo_id}`}>
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))
        }
      </div>
    </div>
  );
}

function SiteSettingsEditor({ settings, onSave }) {
  const [form, setForm] = useState(settings);
  useEffect(() => { setForm(settings); }, [settings]);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault();
    try { await api.put("/site/settings", form); toast.success("Saved"); onSave?.(); }
    catch { toast.error("Save failed"); }
  };
  return (
    <form onSubmit={save} className="border-2 border-black p-6 bg-white grid gap-4 max-w-2xl" data-testid="admin-settings-form">
      <div>
        <label className="overline">Hero title</label>
        <input value={form.hero_title || ""} onChange={set("hero_title")} data-testid="settings-hero-title" />
      </div>
      <div>
        <label className="overline">Hero subtitle</label>
        <textarea rows={2} value={form.hero_subtitle || ""} onChange={set("hero_subtitle")} data-testid="settings-hero-sub" />
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label className="overline">Contact phone</label>
          <input value={form.contact_phone || ""} onChange={set("contact_phone")} data-testid="settings-phone" />
        </div>
        <div>
          <label className="overline">Contact email</label>
          <input value={form.contact_email || ""} onChange={set("contact_email")} data-testid="settings-email" />
        </div>
      </div>
      <div>
        <label className="overline">Service area</label>
        <input value={form.service_area || ""} onChange={set("service_area")} data-testid="settings-area" />
      </div>
      <button className="btn-brutal dark" data-testid="settings-save-btn">Save settings</button>
    </form>
  );
}
