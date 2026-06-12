import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Loader2, Trash2, Plus, Save, Star, FileText } from "lucide-react";
import { toast } from "sonner";

const VAR_HELP = [
  "{{customer_name}}", "{{first_name}}", "{{service_type}}", "{{address}}",
  "{{amount}}", "{{job_id}}", "{{track_url}}", "{{contact_email}}", "{{preferred_date}}",
  "{{breakdown_block}}",
];

export default function EmailTemplatesTab() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(null); // template_id currently being edited
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [mode, setMode] = useState("edit"); // edit | preview

  const refresh = () => {
    setLoading(true);
    api.get("/email-templates").then((r) => setTemplates(r.data || [])).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(() => { refresh(); }, []);

  useEffect(() => {
    if (active && templates.length) {
      const t = templates.find((x) => x.template_id === active);
      if (t) setDraft({ ...t });
    } else if (!active) {
      setDraft(null);
    }
  }, [active, templates]);

  const newTpl = async () => {
    try {
      const r = await api.post("/email-templates", {
        name: "New template",
        subject_template: "Your Nosko quote — Job {{job_id}}",
        html_template: "<div style='font-family:Arial,sans-serif'><p>Hi {{first_name}},</p><p>Quote: <b>${{amount}}</b></p><p>{{breakdown_block}}</p><p>— Nosson</p></div>",
        is_default: false,
      });
      toast.success("Template created");
      refresh();
      setActive(r.data.template_id);
    } catch { toast.error("Could not create"); }
  };

  const save = async () => {
    if (!draft) return;
    setSaving(true);
    try {
      await api.put(`/email-templates/${draft.template_id}`, {
        name: draft.name,
        subject_template: draft.subject_template,
        html_template: draft.html_template,
        is_default: !!draft.is_default,
      });
      toast.success("Saved");
      refresh();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
    finally { setSaving(false); }
  };

  const remove = async (t) => {
    if (!window.confirm(`Delete template "${t.name}"?`)) return;
    try {
      await api.delete(`/email-templates/${t.template_id}`);
      toast.success("Deleted");
      if (active === t.template_id) setActive(null);
      refresh();
    } catch { toast.error("Delete failed"); }
  };

  const setDefault = async (t) => {
    try { await api.put(`/email-templates/${t.template_id}`, { is_default: true }); toast.success(`${t.name} is now default`); refresh(); }
    catch { toast.error("Failed"); }
  };

  // Sample render for preview
  const sampleVars = {
    customer_name: "Alex Rivera", first_name: "Alex", service_type: "Plumbing",
    address: "123 Main St, Dallas, TX", amount: "275.00", job_id: "job_abc12345",
    track_url: "#", contact_email: "noskotx@gmail.com", preferred_date: "2026-07-04 morning",
    breakdown_block: "<table style='width:100%;border-collapse:collapse;margin:8px 0;font-size:14px'><tr><td style='padding:6px 0;border-bottom:1px dashed #ccc'>Labor</td><td style='padding:6px 0;border-bottom:1px dashed #ccc;text-align:right'>$200.00</td></tr><tr><td style='padding:6px 0;border-bottom:1px dashed #ccc'>Materials</td><td style='padding:6px 0;border-bottom:1px dashed #ccc;text-align:right'>$75.00</td></tr></table>",
  };
  const render = (str) => {
    let out = str || "";
    Object.keys(sampleVars).forEach((k) => { out = out.split(`{{${k}}}`).join(sampleVars[k]); });
    return out;
  };

  return (
    <div className="grid lg:grid-cols-3 gap-4" data-testid="templates-section">
      {/* List */}
      <div className="border-2 border-black bg-white lg:col-span-1">
        <div className="p-4 border-b-2 border-black flex items-center justify-between">
          <h2 className="font-display text-lg tracking-tighter inline-flex items-center gap-2"><FileText className="w-4 h-4" /> Templates</h2>
          <button onClick={newTpl} className="overline text-[11px] border-2 border-black px-3 py-1 bg-[#FFD600] hover:bg-yellow-300 inline-flex items-center gap-1" data-testid="tpl-new-btn">
            <Plus className="w-3 h-3" /> New
          </button>
        </div>
        {loading ? <div className="p-4"><Loader2 className="w-4 h-4 animate-spin" /></div> :
          templates.length === 0 ? <p className="p-4 text-sm text-neutral-500">No templates.</p> : (
          <ul className="divide-y divide-black/10">
            {templates.map((t) => (
              <li key={t.template_id} className={`p-3 cursor-pointer ${active === t.template_id ? "bg-[#FFD600]" : "hover:bg-neutral-50"}`} onClick={() => setActive(t.template_id)} data-testid={`tpl-list-${t.template_id}`}>
                <div className="flex items-center justify-between gap-2">
                  <div className="font-display tracking-tight">{t.name} {t.is_default && <Star className="w-3 h-3 inline text-yellow-700" />}</div>
                  <div className="flex items-center gap-1">
                    {!t.is_default && (
                      <button onClick={(e) => { e.stopPropagation(); setDefault(t); }} className="text-[10px] underline" data-testid={`tpl-default-${t.template_id}`}>Set default</button>
                    )}
                    <button onClick={(e) => { e.stopPropagation(); remove(t); }} className="text-red-600 p-1" aria-label="Delete" data-testid={`tpl-del-${t.template_id}`}><Trash2 className="w-3 h-3" /></button>
                  </div>
                </div>
                <div className="text-xs text-neutral-600 truncate mt-1">{t.subject_template}</div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Editor */}
      <div className="border-2 border-black bg-white lg:col-span-2">
        {!draft ? (
          <div className="p-8 text-center text-neutral-500">
            <p>Select a template on the left to edit it,</p>
            <p className="text-sm mt-1">or click <b>New</b> to add one.</p>
          </div>
        ) : (
          <div>
            <div className="p-4 border-b-2 border-black grid sm:grid-cols-2 gap-3">
              <div>
                <label className="overline">Name</label>
                <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} data-testid="tpl-edit-name" />
              </div>
              <div>
                <label className="overline">Default for quotes?</label>
                <label className="flex items-center gap-2 mt-2"><input type="checkbox" checked={!!draft.is_default} onChange={(e) => setDraft({ ...draft, is_default: e.target.checked })} data-testid="tpl-edit-default" /> Yes, send by default</label>
              </div>
            </div>
            <div className="p-4 border-b-2 border-black">
              <label className="overline">Subject template</label>
              <input value={draft.subject_template} onChange={(e) => setDraft({ ...draft, subject_template: e.target.value })} className="font-mono text-sm" data-testid="tpl-edit-subject" />
            </div>
            <div>
              <div className="flex border-b-2 border-black">
                <button type="button" onClick={() => setMode("edit")} className={`overline text-[11px] px-4 py-2 ${mode === "edit" ? "bg-black text-[#FFD600]" : "bg-white"}`} data-testid="tpl-mode-edit">Edit HTML</button>
                <button type="button" onClick={() => setMode("preview")} className={`overline text-[11px] px-4 py-2 ${mode === "preview" ? "bg-black text-[#FFD600]" : "bg-white"}`} data-testid="tpl-mode-preview">Preview (sample data)</button>
              </div>
              {mode === "edit" ? (
                <textarea value={draft.html_template} onChange={(e) => setDraft({ ...draft, html_template: e.target.value })} rows={14} className="w-full font-mono text-xs p-3 border-0 rounded-none focus:ring-0" data-testid="tpl-edit-html" />
              ) : (
                <div className="p-4 bg-neutral-50 max-h-[400px] overflow-y-auto" dangerouslySetInnerHTML={{ __html: render(draft.html_template) }} data-testid="tpl-html-preview" />
              )}
            </div>
            <div className="p-4 border-t-2 border-black bg-neutral-50 flex flex-wrap items-center justify-between gap-2">
              <div className="text-[10px] text-neutral-600 flex flex-wrap gap-1">
                {VAR_HELP.map((v) => <code key={v} className="px-1 bg-white border border-neutral-300">{v}</code>)}
              </div>
              <button onClick={save} disabled={saving} className="overline text-[11px] border-2 border-black px-4 py-2 bg-[#FFD600] hover:bg-yellow-300 disabled:opacity-40 inline-flex items-center gap-2" data-testid="tpl-save-btn">
                {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />} Save template
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
