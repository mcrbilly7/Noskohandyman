import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Loader2, Trash2, Plus, Tag, RefreshCw, Save } from "lucide-react";
import { toast } from "sonner";

export default function DiscountCodesTab() {
  const [codes, setCodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState({}); // {code_id: {percent_off, code, notes}}
  // New code form
  const [newPercent, setNewPercent] = useState(15);
  const [newCode, setNewCode] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [creating, setCreating] = useState(false);

  const refresh = () => {
    setLoading(true);
    api.get("/discount-codes").then((r) => setCodes(r.data || [])).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(() => { refresh(); }, []);

  const create = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post("/discount-codes", {
        percent_off: Number(newPercent),
        code: newCode.trim() || undefined,
        email: newEmail.trim() || undefined,
        notes: newNotes.trim() || undefined,
      });
      toast.success("Code created");
      setNewCode(""); setNewEmail(""); setNewNotes("");
      refresh();
    } catch (e2) { toast.error(e2?.response?.data?.detail || "Could not create"); }
    finally { setCreating(false); }
  };

  const save = async (c) => {
    const patch = editing[c.code_id] || {};
    if (!Object.keys(patch).length) return;
    try {
      await api.put(`/discount-codes/${c.code_id}`, patch);
      toast.success("Updated");
      setEditing({ ...editing, [c.code_id]: undefined });
      refresh();
    } catch (e) { toast.error(e?.response?.data?.detail || "Update failed"); }
  };

  const reset = async (c) => {
    if (!window.confirm(`Reset usage on ${c.code}? It'll be usable again.`)) return;
    try { await api.put(`/discount-codes/${c.code_id}`, { reset_usage: true }); toast.success("Reset"); refresh(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Reset failed"); }
  };

  const remove = async (c) => {
    if (!window.confirm(`Delete ${c.code}? This cannot be undone.`)) return;
    try { await api.delete(`/discount-codes/${c.code_id}`); toast.success("Deleted"); refresh(); }
    catch { toast.error("Delete failed"); }
  };

  const setPatch = (id, k, v) => setEditing({ ...editing, [id]: { ...(editing[id] || {}), [k]: v } });

  return (
    <div className="grid gap-6">
      {/* Create new */}
      <form onSubmit={create} className="border-2 border-black bg-white" data-testid="code-create-form">
        <div className="p-4 border-b-2 border-black bg-[#FFD600] inline-flex items-center gap-2 w-full">
          <Tag className="w-4 h-4" /> <h2 className="font-display text-xl tracking-tighter">Create discount code</h2>
        </div>
        <div className="p-5 grid sm:grid-cols-4 gap-3">
          <div>
            <label className="overline">% off *</label>
            <input type="number" min="1" max="100" required value={newPercent} onChange={(e) => setNewPercent(e.target.value)} data-testid="code-create-percent" />
          </div>
          <div>
            <label className="overline">Code (optional)</label>
            <input value={newCode} onChange={(e) => setNewCode(e.target.value.toUpperCase())} placeholder="Auto if blank" className="font-mono" data-testid="code-create-code" />
          </div>
          <div>
            <label className="overline">Assign to email</label>
            <input type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="Optional" data-testid="code-create-email" />
          </div>
          <div>
            <label className="overline">Note</label>
            <input value={newNotes} onChange={(e) => setNewNotes(e.target.value)} placeholder="e.g. Spring promo" data-testid="code-create-notes" />
          </div>
          <div className="sm:col-span-4 flex justify-end">
            <button type="submit" disabled={creating} className="overline text-[11px] border-2 border-black px-4 py-2 bg-black text-[#FFD600] hover:bg-neutral-800 disabled:opacity-40 inline-flex items-center gap-2" data-testid="code-create-btn">
              {creating ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />} Create code
            </button>
          </div>
        </div>
      </form>

      {/* List */}
      <div className="border-2 border-black bg-white" data-testid="codes-list">
        <div className="p-4 border-b-2 border-black">
          <h2 className="font-display text-xl tracking-tighter">All codes ({codes.length})</h2>
          <p className="text-xs text-neutral-600">Auto-issued on email signup OR manually created above. Click a row to edit.</p>
        </div>
        {loading ? <div className="p-6"><Loader2 className="w-5 h-5 animate-spin" /></div> :
          codes.length === 0 ? <p className="p-6 text-sm text-neutral-500">No codes yet.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[860px]">
              <thead className="bg-neutral-50 border-b border-black">
                <tr>
                  <th className="text-left px-3 py-2 overline">Code</th>
                  <th className="text-left px-3 py-2 overline">% off</th>
                  <th className="text-left px-3 py-2 overline">Email</th>
                  <th className="text-left px-3 py-2 overline">Status</th>
                  <th className="text-left px-3 py-2 overline">Source</th>
                  <th className="text-left px-3 py-2 overline">Notes</th>
                  <th className="text-right px-3 py-2 overline">Actions</th>
                </tr>
              </thead>
              <tbody>
                {codes.map((c) => {
                  const p = editing[c.code_id] || {};
                  const dirty = Object.keys(p).length > 0;
                  return (
                    <tr key={c.code_id} className="border-b border-black/10" data-testid={`code-row-${c.code_id}`}>
                      <td className="px-3 py-2 font-mono text-xs">
                        <input
                          defaultValue={c.code}
                          onChange={(e) => setPatch(c.code_id, "code", e.target.value.toUpperCase())}
                          className="font-mono text-xs w-32"
                          data-testid={`code-input-${c.code_id}`}
                        />
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="number" min="1" max="100"
                          defaultValue={c.percent_off}
                          onChange={(e) => setPatch(c.code_id, "percent_off", parseInt(e.target.value, 10))}
                          className="w-16"
                          data-testid={`code-percent-${c.code_id}`}
                        />
                      </td>
                      <td className="px-3 py-2 text-xs break-all">{c.email || "—"}</td>
                      <td className="px-3 py-2">
                        {c.used_at ? <span className="overline text-[10px] bg-green-200 border border-black px-2 py-0.5">USED</span>
                          : <span className="overline text-[10px] bg-yellow-100 border border-black px-2 py-0.5">UNUSED</span>}
                        {c.used_on_job_id && <div className="text-[10px] text-neutral-600 mt-1 font-mono">{c.used_on_job_id}</div>}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        <span className="overline text-[10px]">{c.created_by === "auto_signup" ? "Signup" : "Manual"}</span>
                      </td>
                      <td className="px-3 py-2">
                        <input
                          defaultValue={c.notes}
                          onChange={(e) => setPatch(c.code_id, "notes", e.target.value)}
                          placeholder="add note"
                          className="text-xs w-40"
                          data-testid={`code-notes-${c.code_id}`}
                        />
                      </td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        {dirty && (
                          <button onClick={() => save(c)} className="p-1 mr-1 inline-flex items-center text-green-700" aria-label="Save" data-testid={`code-save-${c.code_id}`}><Save className="w-4 h-4" /></button>
                        )}
                        {c.used_at && (
                          <button onClick={() => reset(c)} className="p-1 mr-1 text-amber-700" aria-label="Reset" title="Reset usage" data-testid={`code-reset-${c.code_id}`}><RefreshCw className="w-4 h-4" /></button>
                        )}
                        <button onClick={() => remove(c)} className="text-red-600 p-1" aria-label="Delete" data-testid={`code-del-${c.code_id}`}><Trash2 className="w-4 h-4" /></button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
