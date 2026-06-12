import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Calendar } from "@/components/ui/calendar";
import { CalendarOff, Loader2, Save } from "lucide-react";
import { toast } from "sonner";

const WEEKDAYS = [
  { id: "mon", label: "Mon" },
  { id: "tue", label: "Tue" },
  { id: "wed", label: "Wed" },
  { id: "thu", label: "Thu" },
  { id: "fri", label: "Fri" },
  { id: "sat", label: "Sat" },
  { id: "sun", label: "Sun" },
];
// JS Date.getDay(): 0=Sun..6=Sat. Map to our 3-letter labels.
const JS_DOW_TO_LABEL = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

const fmt = (d) => {
  if (!d) return "";
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
};

function useIsNarrow(bp = 768) {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.innerWidth < bp);
  useEffect(() => {
    const onResize = () => setNarrow(window.innerWidth < bp);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [bp]);
  return narrow;
}

export default function AvailabilityEditor() {
  const [blocked, setBlocked] = useState([]);
  const [weekdays, setWeekdays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const isNarrow = useIsNarrow();

  useEffect(() => {
    api.get("/availability").then((r) => {
      setBlocked(r.data?.blocked_dates || []);
      setWeekdays(r.data?.blocked_weekdays || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const blockedDateObjs = blocked.map((s) => {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(y, m - 1, d);
  });

  const toggleDate = (date) => {
    if (!date) return;
    const key = fmt(date);
    setBlocked((prev) => prev.includes(key) ? prev.filter((x) => x !== key) : [...prev, key].sort());
  };

  const toggleWeekday = (id) => {
    setWeekdays((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/availability", { blocked_dates: blocked, blocked_weekdays: weekdays });
      toast.success("Schedule saved");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  const today = new Date(); today.setHours(0, 0, 0, 0);

  if (loading) return <div className="border-2 border-black p-6 bg-white"><Loader2 className="w-5 h-5 animate-spin" /></div>;

  return (
    <div className="grid gap-4" data-testid="admin-availability-section">
      {/* Recurring weekday off-days */}
      <div className="border-2 border-black bg-white">
        <div className="p-5 border-b border-black bg-[#F9FAFB]">
          <div className="overline">Days off — every week</div>
          <div className="font-display text-2xl tracking-tighter mt-1">I never work on…</div>
          <p className="text-sm text-neutral-600 mt-1">These weekdays will be greyed out on the customer calendar every week, automatically.</p>
        </div>
        <div className="p-5 flex flex-wrap gap-2" data-testid="weekday-toggles">
          {WEEKDAYS.map((w) => (
            <button
              key={w.id}
              type="button"
              onClick={() => toggleWeekday(w.id)}
              className={`px-4 py-2 border-2 border-black overline ${weekdays.includes(w.id) ? "bg-red-200 line-through" : "bg-white hover:bg-neutral-50"}`}
              data-testid={`weekday-${w.id}`}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {/* Specific date blocks */}
      <div className="border-2 border-black bg-white">
        <div className="p-5 border-b border-black bg-[#F9FAFB] flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="overline">Specific dates off</div>
            <div className="font-display text-2xl tracking-tighter mt-1">Vacation / one-off days</div>
            <p className="text-sm text-neutral-600 mt-1">Click any future day to block (or unblock) it.</p>
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
              onSelect={toggleDate}
              modifiers={{ blocked: blockedDateObjs, weeklyOff: (d) => weekdays.includes(JS_DOW_TO_LABEL[d.getDay()]) }}
              modifiersClassNames={{ blocked: "bg-red-200 line-through", weeklyOff: "bg-red-50 text-neutral-400" }}
              disabled={(d) => d < today}
              numberOfMonths={isNarrow ? 1 : 2}
              data-testid="availability-calendar"
            />
            <p className="text-xs text-neutral-500 mt-3">
              <span className="bg-red-200 px-1">Red strike</span> = blocked date · <span className="bg-red-50 px-1 text-neutral-500">Light red</span> = recurring weekday off
            </p>
          </div>
          <div className="p-5 bg-[#F9FAFB]">
            <div className="overline">Blocked days ({blocked.length})</div>
            {blocked.length === 0 ? (
              <p className="text-sm text-neutral-500 mt-2">No one-off blocks. Use weekday toggles above for recurring days.</p>
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
              <CalendarOff className="w-4 h-4" /> Clear all dates
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
