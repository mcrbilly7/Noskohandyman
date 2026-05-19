import React from "react";

export default function Footer() {
  return (
    <footer className="border-t-2 border-black mt-24 bg-white">
      <div className="caution-tape" />
      <div className="max-w-[1400px] mx-auto px-6 py-12 grid md:grid-cols-3 gap-10">
        <div>
          <div className="font-display text-3xl tracking-tighter">NOSKO</div>
          <p className="text-sm mt-3 max-w-xs text-neutral-600">
            Fixed-price handyman services. $25 minimum. Real workers. W9-compliant pay.
          </p>
        </div>
        <div>
          <div className="overline mb-3">Services</div>
          <ul className="space-y-1 text-sm">
            <li>Switch Replacement — $25</li>
            <li>Outlet Replacement — $25</li>
            <li>$25 minimum on every job</li>
          </ul>
        </div>
        <div>
          <div className="overline mb-3">For workers</div>
          <ul className="space-y-1 text-sm">
            <li>W9-compliant 1099 work</li>
            <li>Weekly earnings dashboard</li>
            <li>Marketer profit share — 15%</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-black/10 py-4 text-center overline text-xs text-neutral-500">
        © {new Date().getFullYear()} NOSKO HANDYMAN CO.
      </div>
    </footer>
  );
}
