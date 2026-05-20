import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Calendar } from "@/components/ui/calendar";
import { CalendarOff, Loader2, Save } from "lucide-react";
import { toast } from "sonner";

const fmt = (d) => {
  if (!d) return "";
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
};

export default function AvailabilityEditor() {
  const [blocked, setBlocked] = useState([]);  // YYYY-MM-DD strings
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/availability").then((r) => {
      setBlocked(r.data?.blocked_dates || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const blockedSet = new Set(blocked);
  const blockedDateObjs = blocked.map((s) => {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(y, m - 1, d);
  });

  const toggle = (date) => {
    if (!date) return;
    const key = fmt(date);
    setBlocked((prev) => prev.includes(key) ? prev.filter((x) => x !== key) : [...prev, key].sort());
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/availability", { blocked_dates: blocked });
      toast.success("Schedule saved");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  const today = new Date(); today.setHours(0, 0, 0, 0);

  if (loading) return <div className="border-2 border-black p-6 bg-white"><Loader2 className="w-5 h-5 animate-spin" /></div>;

  return (
    <div className="border-2 border-black bg-white" data-testid="admin-availability-section">
      <div className="p-5 border-b border-black bg-[#F9FAFB] flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="overline">My schedule</div>
          <div className="font-display text-2xl tracking-tighter mt-1">Days I can't work</div>
          <p className="text-sm text-neutral-600 mt-1">Click a day to block it. Blocked days won't be selectable on the customer quote form.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="overline text-[10px] border border-black px-2 py-1 bg-white" data-testid="blocked-count">{blocked.length} blocked</span>
          <button className="btn-brutal dark" onClick={save} disabled={saving} data-testid="availability-save-btn">
            {saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</> : <><Save className="w-4 h-4" /> Save schedule</>}
          </button>
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_280px] gap-0">
        <div className="p-5 border-r-0 lg:border-r border-black">
          <Calendar
            mode="single"
            onSelect={toggle}
            modifiers={{ blocked: blockedDateObjs }}
            modifiersClassNames={{ blocked: "bg-red-200 line-through" }}
            disabled={(d) => d < today}
            numberOfMonths={2}
            data-testid="availability-calendar"
          />
          <p className="text-xs text-neutral-500 mt-3">Past days are auto-disabled. <span className="bg-red-200 px-1">Red strike</span> = blocked.</p>
        </div>
        <div className="p-5 bg-[#F9FAFB]">
          <div className="overline">Blocked days ({blocked.length})</div>
          {blocked.length === 0 ? (
            <p className="text-sm text-neutral-500 mt-2">You're open every day. Click any future day on the calendar to block it.</p>
          ) : (
            <ul className="mt-3 grid gap-1 max-h-96 overflow-auto">
              {blocked.map((d) => (
                <li key={d} className="flex items-center justify-between border border-black px-2 py-1 text-sm">
                  <span className="font-mono">{d}</span>
                  <button type="button" className="overline text-[10px] hover:bg-red-50 px-2" onClick={() => setBlocked((p) => p.filter((x) => x !== d))} data-testid={`unblock-${d}`}>×</button>
                </li>
              ))}
            </ul>
          )}
          <button type="button" className="btn-brutal ghost mt-4 w-full" onClick={() => setBlocked([])} data-testid="clear-all-blocked">
            <CalendarOff className="w-4 h-4" /> Clear all
          </button>
        </div>
      </div>
    </div>
  );
}
