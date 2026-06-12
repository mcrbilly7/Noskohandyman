import React, { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, MapPin, Clock } from "lucide-react";

const TIME_SLOT_LABELS = {
  morning: "AM",
  afternoon: "PM",
  evening: "Eve",
  flexible: "Flex",
};

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function fmt(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function startOfWeek(d) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  x.setDate(x.getDate() - x.getDay());  // back to Sunday
  return x;
}

/** "My week" view — groups jobs by preferred_date in a 7-day window. */
export default function MyWeekView({ jobs }) {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));

  const days = useMemo(() => {
    const arr = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(weekStart);
      d.setDate(d.getDate() + i);
      arr.push(d);
    }
    return arr;
  }, [weekStart]);

  const byDate = useMemo(() => {
    const map = {};
    for (const j of jobs || []) {
      if (!j.preferred_date) continue;
      (map[j.preferred_date] ||= []).push(j);
    }
    return map;
  }, [jobs]);

  const unscheduled = useMemo(
    () => (jobs || []).filter((j) => !j.preferred_date && j.status !== "completed" && j.status !== "cancelled"),
    [jobs]
  );

  const shift = (delta) => {
    const x = new Date(weekStart);
    x.setDate(x.getDate() + delta * 7);
    setWeekStart(x);
  };

  const today = fmt(new Date());

  return (
    <div className="border-2 border-black bg-white" data-testid="my-week-view">
      <div className="p-4 border-b border-black bg-[#FFD600] flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="overline">My week</div>
          <div className="font-display text-2xl tracking-tighter">
            {weekStart.toLocaleDateString("en-US", { month: "short", day: "numeric" })} – {new Date(weekStart.getTime() + 6 * 86400000).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
          </div>
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn-brutal ghost" onClick={() => shift(-1)} data-testid="week-prev"><ChevronLeft className="w-4 h-4" /> Prev</button>
          <button type="button" className="btn-brutal" onClick={() => setWeekStart(startOfWeek(new Date()))} data-testid="week-today">This week</button>
          <button type="button" className="btn-brutal ghost" onClick={() => shift(1)} data-testid="week-next">Next <ChevronRight className="w-4 h-4" /></button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7">
        {days.map((d) => {
          const key = fmt(d);
          const list = byDate[key] || [];
          const isToday = key === today;
          return (
            <div key={key} className={`border-r border-b border-black p-3 min-h-[180px] ${isToday ? "bg-[#FFFBE6]" : ""}`} data-testid={`week-col-${key}`}>
              <div className="flex items-baseline justify-between">
                <div>
                  <div className="overline text-[10px]">{DAY_NAMES[d.getDay()]}</div>
                  <div className="font-display text-2xl tracking-tighter">{d.getDate()}</div>
                </div>
                {isToday && <span className="overline text-[9px] bg-black text-[#FFD600] px-1.5 py-0.5">TODAY</span>}
              </div>
              <div className="mt-2 grid gap-1.5">
                {list.length === 0 ? (
                  <span className="text-xs text-neutral-400">—</span>
                ) : list.map((j) => (
                  <div key={j.job_id} className="border border-black bg-white p-2 text-xs" data-testid={`week-job-${j.job_id}`}>
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-display tracking-tight truncate">{j.customer_name}</span>
                      <span className="overline text-[9px] bg-black text-[#FFD600] px-1">{TIME_SLOT_LABELS[j.preferred_time_slot] || j.preferred_time_slot || "?"}</span>
                    </div>
                    <div className="text-neutral-600 mt-0.5 flex items-start gap-1">
                      <MapPin className="w-3 h-3 mt-0.5 shrink-0" /> <span className="truncate">{j.address}</span>
                    </div>
                    <div className="text-[10px] text-neutral-500 mt-0.5">{j.service_type}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {unscheduled.length > 0 && (
        <div className="p-4 border-t-2 border-black bg-neutral-50">
          <div className="overline flex items-center gap-1"><Clock className="w-3 h-3" /> No date picked ({unscheduled.length})</div>
          <div className="flex flex-wrap gap-2 mt-2">
            {unscheduled.slice(0, 12).map((j) => (
              <span key={j.job_id} className="text-xs border border-black bg-white px-2 py-1" data-testid={`week-unscheduled-${j.job_id}`}>
                {j.customer_name} · <span className="text-neutral-500">{j.service_type}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
