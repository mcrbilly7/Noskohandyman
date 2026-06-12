import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Loader2, Send, Trash2, Mail, Eye } from "lucide-react";
import { toast } from "sonner";

export default function EmailListTab() {
  const [subs, setSubs] = useState([]);
  const [blasts, setBlasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [subject, setSubject] = useState("");
  const [html, setHtml] = useState(
    `<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#0A0A0A">\n  <h2 style="font-family:Arial,sans-serif">Hey from Nosko</h2>\n  <p>Quick update from the shop...</p>\n  <p>— Nosson</p>\n</div>`
  );
  const [mode, setMode] = useState("edit");
  const [sending, setSending] = useState(false);
  const [previewing, setPreviewing] = useState(false);

  const refresh = () => {
    setLoading(true);
    Promise.all([
      api.get("/subscribers").then((r) => setSubs(r.data || [])).catch(() => {}),
      api.get("/email-blasts").then((r) => setBlasts(r.data || [])).catch(() => {}),
    ]).finally(() => setLoading(false));
  };
  useEffect(() => { refresh(); }, []);

  const removeSub = async (sub_id) => {
    if (!window.confirm("Remove this subscriber?")) return;
    try { await api.delete(`/subscribers/${sub_id}`); toast.success("Removed"); refresh(); }
    catch { toast.error("Failed"); }
  };

  const sendBlast = async () => {
    if (!subject.trim() || !html.trim()) { toast.error("Subject + body required"); return; }
    if (!window.confirm(`Send "${subject}" to ${subs.length} subscriber${subs.length === 1 ? "" : "s"}?`)) return;
    setSending(true);
    try {
      const r = await api.post("/email-blasts", { subject, html });
      toast.success(`Sent to ${r.data.sent_count} of ${r.data.recipient_count}`);
      setSubject(""); refresh();
    } catch (e) { toast.error(e?.response?.data?.detail || "Send failed"); }
    finally { setSending(false); }
  };

  const preview = async () => {
    setPreviewing(true);
    try {
      const r = await api.post("/email-blasts/preview", { subject, html });
      toast.success(`Will send to ${r.data.recipient_count} subscriber${r.data.recipient_count === 1 ? "" : "s"}`);
    } catch (e) { toast.error(e?.response?.data?.detail || "Preview failed"); }
    finally { setPreviewing(false); }
  };

  return (
    <div className="grid gap-6">
      {/* Compose blast */}
      <div className="border-2 border-black bg-white" data-testid="email-blast-section">
        <div className="p-4 border-b-2 border-black bg-[#0A0A0A] text-white flex items-center gap-2">
          <Mail className="w-4 h-4 text-[#FFD600]" />
          <h2 className="font-display text-xl tracking-tighter">Email blast — write & send to your list</h2>
        </div>
        <div className="p-5 grid gap-4">
          <div className="text-sm">
            Recipients: <b>{subs.length}</b> subscriber{subs.length === 1 ? "" : "s"}
          </div>
          <div>
            <label className="overline">Subject</label>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Spring deal — 10% off May bookings" data-testid="blast-subject" />
          </div>
          <div className="border-2 border-black">
            <div className="flex border-b-2 border-black">
              <button type="button" onClick={() => setMode("edit")} className={`overline text-[11px] px-4 py-2 ${mode === "edit" ? "bg-black text-[#FFD600]" : "bg-white"}`} data-testid="blast-mode-edit">Edit HTML</button>
              <button type="button" onClick={() => setMode("preview")} className={`overline text-[11px] px-4 py-2 ${mode === "preview" ? "bg-black text-[#FFD600]" : "bg-white"}`} data-testid="blast-mode-preview">Preview</button>
            </div>
            {mode === "edit" ? (
              <textarea value={html} onChange={(e) => setHtml(e.target.value)} rows={12} className="w-full font-mono text-xs p-3 border-0 rounded-none focus:ring-0" data-testid="blast-html" />
            ) : (
              <div className="p-4 bg-neutral-50 max-h-[400px] overflow-y-auto" dangerouslySetInnerHTML={{ __html: html }} data-testid="blast-html-preview" />
            )}
          </div>
          <div className="flex flex-wrap gap-2 justify-end">
            <button type="button" onClick={preview} disabled={previewing || !subject.trim()} className="overline text-[11px] border-2 border-black px-4 py-2 bg-white hover:bg-neutral-50 disabled:opacity-40 inline-flex items-center gap-2" data-testid="blast-preview-btn">
              {previewing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Eye className="w-3 h-3" />} Preview count
            </button>
            <button type="button" onClick={sendBlast} disabled={sending || !subject.trim() || subs.length === 0} className="overline text-[11px] border-2 border-black px-4 py-2 bg-[#FFD600] hover:bg-yellow-300 disabled:opacity-40 inline-flex items-center gap-2" data-testid="blast-send-btn">
              {sending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />} Send to {subs.length}
            </button>
          </div>
        </div>
      </div>

      {/* Subscriber list */}
      <div className="border-2 border-black bg-white" data-testid="subscribers-section">
        <div className="p-4 border-b-2 border-black flex flex-wrap justify-between items-center gap-2">
          <h2 className="font-display text-xl tracking-tighter">Subscribers ({subs.length})</h2>
        </div>
        {loading ? <div className="p-6"><Loader2 className="w-5 h-5 animate-spin" /></div> :
          subs.length === 0 ? <p className="p-6 text-sm text-neutral-500">No subscribers yet. Promote the email signup on the landing page.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[640px]">
              <thead className="bg-neutral-50 border-b border-black">
                <tr>
                  <th className="text-left px-4 py-2 overline">Email</th>
                  <th className="text-left px-4 py-2 overline">Code</th>
                  <th className="text-left px-4 py-2 overline">% off</th>
                  <th className="text-left px-4 py-2 overline">Status</th>
                  <th className="text-left px-4 py-2 overline">Joined</th>
                  <th className="text-right px-4 py-2 overline">Actions</th>
                </tr>
              </thead>
              <tbody>
                {subs.map((s) => (
                  <tr key={s.sub_id} className="border-b border-black/10" data-testid={`sub-row-${s.sub_id}`}>
                    <td className="px-4 py-2 break-all">{s.email}</td>
                    <td className="px-4 py-2 font-mono text-xs">{s.code || "—"}</td>
                    <td className="px-4 py-2">{s.percent_off ? `${s.percent_off}%` : "—"}</td>
                    <td className="px-4 py-2">
                      {s.code_used ? <span className="overline text-[10px] bg-green-200 border border-black px-2 py-0.5">USED</span>
                        : s.code ? <span className="overline text-[10px] bg-yellow-100 border border-black px-2 py-0.5">UNUSED</span>
                        : <span className="overline text-[10px] text-neutral-500">—</span>}
                    </td>
                    <td className="px-4 py-2 text-xs text-neutral-600">{new Date(s.subscribed_at).toLocaleDateString()}</td>
                    <td className="px-4 py-2 text-right">
                      <button onClick={() => removeSub(s.sub_id)} className="text-red-600 p-1" aria-label="Remove" data-testid={`sub-del-${s.sub_id}`}><Trash2 className="w-4 h-4" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Past blasts */}
      <div className="border-2 border-black bg-white">
        <div className="p-4 border-b-2 border-black">
          <h2 className="font-display text-xl tracking-tighter">Past email blasts</h2>
        </div>
        {blasts.length === 0 ? <p className="p-6 text-sm text-neutral-500">No emails sent yet.</p> : (
          <div className="divide-y divide-black/10">
            {blasts.map((b) => (
              <div key={b.blast_id} className="p-4 flex flex-wrap items-center justify-between gap-2" data-testid={`blast-row-${b.blast_id}`}>
                <div>
                  <div className="font-display text-base tracking-tight">{b.subject}</div>
                  <div className="text-xs text-neutral-600 mt-1">
                    Sent {new Date(b.sent_at).toLocaleString()} · {b.sent_count}/{b.recipient_count} delivered
                    {b.failed_count ? ` · ${b.failed_count} failed` : ""}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
