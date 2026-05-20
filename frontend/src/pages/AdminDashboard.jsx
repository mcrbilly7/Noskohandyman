import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api, fileUrl } from "@/lib/api";
import DashboardLayout from "@/components/layout/DashboardLayout";
import FileUploader from "@/components/shared/FileUploader";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Image as ImageIcon, Trash2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

const FOUNDING_EMAILS = ["noskotx@gmail.com", "nossonkosowsky32@gmail.com"];

export default function AdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState({});
  const [jobs, setJobs] = useState([]);
  const [users, setUsers] = useState([]);
  const [portfolio, setPortfolio] = useState([]);
  const [settings, setSettings] = useState({});

  const isFounder = user?.email && FOUNDING_EMAILS.includes(user.email.toLowerCase());

  const refreshAll = () => {
    api.get("/admin/stats").then((r) => setStats(r.data)).catch(() => {});
    api.get("/jobs").then((r) => setJobs(r.data || [])).catch(() => {});
    api.get("/admin/users").then((r) => setUsers(r.data || [])).catch(() => {});
    api.get("/portfolio").then((r) => setPortfolio(r.data || [])).catch(() => {});
    api.get("/site/settings").then((r) => setSettings(r.data)).catch(() => {});
  };

  useEffect(() => { refreshAll(); }, []);

  const setStatus = async (jobId, status) => {
    try { await api.put(`/jobs/${jobId}/status`, { status }); toast.success("Updated"); refreshAll(); }
    catch { toast.error("Update failed"); }
  };
  const changeRole = async (uid, role) => {
    try { await api.put(`/admin/users/${uid}/role`, { role }); toast.success("Role updated"); refreshAll(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <DashboardLayout role="admin">
      <div className="p-8 max-w-[1400px]">
        <div className="overline">Admin</div>
        <h1 className="font-display text-4xl tracking-tighter mt-1" data-testid="admin-title">Command center</h1>

        <div className="grid md:grid-cols-4 gap-0 border border-black mt-6" data-testid="admin-stats">
          {[
            { l: "New jobs", v: stats.jobs_new || 0, hl: true },
            { l: "Total jobs", v: stats.jobs_total || 0 },
            { l: "Completed", v: stats.jobs_completed || 0 },
            { l: "All users", v: stats.users_total || 0 },
          ].map((c) => (
            <div key={c.l} className={`p-5 border-r border-black last:border-r-0 ${c.hl ? "bg-[#FFD600]" : "bg-white"}`}>
              <div className="overline">{c.l}</div>
              <div className="font-display text-3xl tracking-tighter mt-1">{c.v}</div>
            </div>
          ))}
        </div>

        <Tabs defaultValue="jobs" className="mt-8">
          <TabsList className="bg-black text-white rounded-none border-2 border-black p-0 h-auto flex flex-wrap">
            {[
              ["jobs", "Quote requests"], ["team", "Team"], ["portfolio", "Portfolio"], ["settings", "Edit website"],
            ].map(([v, l]) => (
              <TabsTrigger key={v} value={v} className="rounded-none data-[state=active]:bg-[#FFD600] data-[state=active]:text-black overline px-4 py-2" data-testid={`tab-${v}`}>{l}</TabsTrigger>
            ))}
          </TabsList>

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
                      </div>
                      <div className="lg:col-span-3">
                        <div className="overline">Update status</div>
                        <select className="mt-1" onChange={(e) => setStatus(j.job_id, e.target.value)} value={j.status} data-testid={`status-${j.job_id}`}>
                          <option value="new">new</option><option value="assigned">assigned</option><option value="in_progress">in_progress</option><option value="completed">completed</option><option value="cancelled">cancelled</option>
                        </select>
                        <a href={`/track/${j.job_id}`} target="_blank" rel="noreferrer" className="overline text-[10px] underline mt-2 inline-block" data-testid={`track-link-${j.job_id}`}>
                          View customer tracking page →
                        </a>
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

          <TabsContent value="team" className="mt-4">
            <div className="border-2 border-black bg-white" data-testid="admin-team-section">
              <div className="p-4 border-b border-black bg-[#F9FAFB] flex items-center justify-between">
                <div>
                  <div className="overline">All users · {users.length}</div>
                  <div className="text-sm text-neutral-700">Founders can change anyone's role. Admins & developers see this list read-only.</div>
                </div>
                {!isFounder && <span className="overline text-[10px] inline-flex items-center gap-1 bg-yellow-100 border border-black px-2 py-1"><ShieldAlert className="w-3 h-3" /> Founder-only edits</span>}
              </div>
              <table className="w-full text-sm">
                <thead className="bg-[#F9FAFB] overline text-[10px]">
                  <tr><th className="p-3 text-left">User</th><th className="p-3 text-left">Auth</th><th className="p-3 text-left">Role</th><th className="p-3 text-left">Joined</th><th className="p-3 text-right">{isFounder ? "Set role" : ""}</th></tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const isThisFounder = FOUNDING_EMAILS.includes((u.email || "").toLowerCase());
                    return (
                      <tr key={u.user_id} className="border-t border-neutral-200">
                        <td className="p-3">
                          <div className="font-display tracking-tight">{u.name}</div>
                          <div className="font-mono text-xs text-neutral-500">{u.email}</div>
                          {isThisFounder && <span className="overline text-[9px] bg-[#FFD600] border border-black px-1.5 py-0.5">FOUNDER</span>}
                        </td>
                        <td className="p-3 text-xs uppercase font-mono">{u.auth_provider || "—"}</td>
                        <td className="p-3"><span className="overline text-[10px] bg-black text-[#FFD600] px-2 py-0.5 capitalize">{u.role}</span></td>
                        <td className="p-3 text-xs text-neutral-500">{u.created_at?.slice(0, 10)}</td>
                        <td className="p-3 text-right">
                          {isFounder && !isThisFounder ? (
                            <select value={u.role} onChange={(e) => changeRole(u.user_id, e.target.value)} data-testid={`role-${u.user_id}`}>
                              <option value="customer">customer</option>
                              <option value="worker">worker</option>
                              <option value="marketer">marketer</option>
                              <option value="developer">developer</option>
                              <option value="admin">admin</option>
                            </select>
                          ) : <span className="text-xs text-neutral-400">—</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="portfolio" className="mt-4">
            <PortfolioEditor portfolio={portfolio} refresh={refreshAll} />
          </TabsContent>

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
      for (const p of paths) await api.post("/portfolio", { title, description: desc, storage_path: p });
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
  const setNum = (k) => (e) => setForm({ ...form, [k]: parseFloat(e.target.value) });
  const setItem = (listKey, idx, field) => (e) => {
    const list = [...(form[listKey] || [])];
    list[idx] = { ...list[idx], [field]: e.target.value };
    setForm({ ...form, [listKey]: list });
  };
  const addItem = (listKey, template) => () => {
    setForm({ ...form, [listKey]: [...(form[listKey] || []), template] });
  };
  const removeItem = (listKey, idx) => () => {
    const list = [...(form[listKey] || [])];
    list.splice(idx, 1);
    setForm({ ...form, [listKey]: list });
  };
  const save = async (e) => {
    e.preventDefault();
    try { await api.put("/site/settings", form); toast.success("Saved — landing page updated"); onSave?.(); }
    catch { toast.error("Save failed"); }
  };
  if (!form) return null;

  const Section = ({ title, children }) => (
    <div className="border-2 border-black bg-white p-6 grid gap-4">
      <div className="overline border-b border-black pb-2">{title}</div>
      {children}
    </div>
  );

  return (
    <form onSubmit={save} className="grid gap-6" data-testid="admin-settings-form">
      <Section title="Brand & contact">
        <div className="grid md:grid-cols-2 gap-4">
          <div><label className="overline">Website domain</label><input value={form.website_domain || ""} onChange={set("website_domain")} data-testid="settings-domain" /></div>
          <div><label className="overline">Service area</label><input value={form.service_area || ""} onChange={set("service_area")} data-testid="settings-area" /></div>
          <div><label className="overline">Contact phone</label><input value={form.contact_phone || ""} onChange={set("contact_phone")} data-testid="settings-phone" /></div>
          <div><label className="overline">Contact email</label><input value={form.contact_email || ""} onChange={set("contact_email")} data-testid="settings-email" /></div>
          <div><label className="overline">Outlet/switch price ($)</label><input type="number" min="0" step="0.01" value={form.outlet_price ?? 25} onChange={setNum("outlet_price")} data-testid="settings-outlet" /></div>
          <div><label className="overline">Visit minimum ($)</label><input type="number" min="0" step="0.01" value={form.minimum_charge ?? 50} onChange={setNum("minimum_charge")} data-testid="settings-min" /></div>
        </div>
      </Section>

      <Section title="Hero (top of landing page)">
        <div><label className="overline">Hero title</label><input value={form.hero_title || ""} onChange={set("hero_title")} data-testid="settings-hero-title" /></div>
        <div><label className="overline">Hero subtitle</label><textarea rows={2} value={form.hero_subtitle || ""} onChange={set("hero_subtitle")} data-testid="settings-hero-sub" /></div>
        <div className="grid md:grid-cols-2 gap-4">
          <div><label className="overline">Primary CTA label</label><input value={form.cta_primary_label || ""} onChange={set("cta_primary_label")} data-testid="settings-cta-primary" /></div>
          <div><label className="overline">Secondary CTA label</label><input value={form.cta_secondary_label || ""} onChange={set("cta_secondary_label")} data-testid="settings-cta-secondary" /></div>
        </div>
      </Section>

      <Section title="Services section">
        <div className="grid md:grid-cols-3 gap-4">
          <div><label className="overline">Overline</label><input value={form.services_overline || ""} onChange={set("services_overline")} /></div>
          <div className="md:col-span-2"><label className="overline">Heading</label><input value={form.services_heading || ""} onChange={set("services_heading")} /></div>
        </div>
        <div><label className="overline">Custom subheading (optional)</label><textarea rows={2} value={form.services_subheading || ""} onChange={set("services_subheading")} placeholder="Leave empty to auto-generate from $ amounts" /></div>
        <div>
          <div className="overline mb-2">Service tiles ({(form.services || []).length})</div>
          <div className="grid gap-3">
            {(form.services || []).map((sv, i) => (
              <div key={i} className="grid grid-cols-[1fr_2fr_auto] gap-2 items-start" data-testid={`service-row-${i}`}>
                <input placeholder="Title" value={sv.title || ""} onChange={setItem("services", i, "title")} data-testid={`service-title-${i}`} />
                <input placeholder="Description" value={sv.description || ""} onChange={setItem("services", i, "description")} data-testid={`service-desc-${i}`} />
                <button type="button" className="overline border border-black px-2 py-1 hover:bg-red-50" onClick={removeItem("services", i)} data-testid={`service-del-${i}`}>×</button>
              </div>
            ))}
          </div>
          <button type="button" className="btn-brutal ghost mt-3" onClick={addItem("services", { title: "", description: "" })} data-testid="add-service-btn">+ Add service</button>
        </div>
      </Section>

      <Section title="How it works">
        <div className="grid md:grid-cols-2 gap-4">
          <div><label className="overline">Overline</label><input value={form.how_overline || ""} onChange={set("how_overline")} /></div>
          <div><label className="overline">Heading</label><input value={form.how_heading || ""} onChange={set("how_heading")} /></div>
        </div>
        <div className="grid gap-3">
          {(form.how_it_works || []).map((step, i) => (
            <div key={i} className="grid grid-cols-[1fr_2fr_auto] gap-2 items-start" data-testid={`step-row-${i}`}>
              <input placeholder="Step title" value={step.title || ""} onChange={setItem("how_it_works", i, "title")} data-testid={`step-title-${i}`} />
              <input placeholder="Step description" value={step.description || ""} onChange={setItem("how_it_works", i, "description")} data-testid={`step-desc-${i}`} />
              <button type="button" className="overline border border-black px-2 py-1 hover:bg-red-50" onClick={removeItem("how_it_works", i)}>×</button>
            </div>
          ))}
        </div>
        <button type="button" className="btn-brutal ghost mt-1" onClick={addItem("how_it_works", { title: "", description: "" })}>+ Add step</button>
      </Section>

      <Section title="Programs section">
        <div className="grid md:grid-cols-2 gap-4">
          <div><label className="overline">Overline</label><input value={form.programs_overline || ""} onChange={set("programs_overline")} /></div>
          <div><label className="overline">Heading</label><input value={form.programs_heading || ""} onChange={set("programs_heading")} /></div>
        </div>
        <div className="border border-black p-4 grid gap-3">
          <div className="overline">Worker program card</div>
          <div><label className="overline">Title</label><input value={form.worker_program_title || ""} onChange={set("worker_program_title")} /></div>
          <div><label className="overline">Body</label><textarea rows={2} value={form.worker_program_body || ""} onChange={set("worker_program_body")} /></div>
          <div><label className="overline">CTA button label</label><input value={form.worker_program_cta || ""} onChange={set("worker_program_cta")} /></div>
        </div>
        <div className="border border-black p-4 grid gap-3 bg-[#FFFBE6]">
          <div className="overline">Marketer program card</div>
          <div><label className="overline">Title</label><input value={form.marketer_program_title || ""} onChange={set("marketer_program_title")} /></div>
          <div><label className="overline">Body</label><textarea rows={2} value={form.marketer_program_body || ""} onChange={set("marketer_program_body")} /></div>
          <div><label className="overline">CTA button label</label><input value={form.marketer_program_cta || ""} onChange={set("marketer_program_cta")} /></div>
        </div>
      </Section>

      <Section title="Final CTA strip + Footer">
        <div className="grid md:grid-cols-3 gap-4">
          <div><label className="overline">Overline</label><input value={form.final_cta_overline || ""} onChange={set("final_cta_overline")} /></div>
          <div><label className="overline">Heading</label><input value={form.final_cta_heading || ""} onChange={set("final_cta_heading")} /></div>
          <div><label className="overline">Button label</label><input value={form.final_cta_label || ""} onChange={set("final_cta_label")} /></div>
        </div>
        <div><label className="overline">Footer tagline</label><textarea rows={2} value={form.footer_tagline || ""} onChange={set("footer_tagline")} /></div>
      </Section>

      <div className="sticky bottom-4 z-10 flex justify-end">
        <button className="btn-brutal dark" data-testid="settings-save-btn">Save all changes</button>
      </div>
    </form>
  );
}
