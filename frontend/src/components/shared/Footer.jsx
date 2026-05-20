import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";

export default function Footer({ settings: passedSettings }) {
  const [settings, setSettings] = useState(passedSettings || null);

  useEffect(() => {
    if (passedSettings) { setSettings(passedSettings); return; }
    api.get("/site/settings").then((r) => setSettings(r.data)).catch(() => {});
  }, [passedSettings]);

  const tagline = settings?.footer_tagline || "Full-service handyman based in the DFW Metroplex.";
  const email = settings?.contact_email || "noskotx@gmail.com";
  const domain = settings?.website_domain || "noskotx.com";

  return (
    <footer className="border-t border-black/10 mt-0 bg-white">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-14 grid md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <div className="font-display text-3xl tracking-tighter">NOSKO</div>
          <p className="text-sm mt-3 max-w-sm text-neutral-600">{tagline}</p>
          <a href={`mailto:${email}`} className="overline mt-4 inline-block" data-testid="footer-email">{email}</a>
          <div className="overline mt-1 text-neutral-500">{domain}</div>
        </div>
        <div>
          <div className="overline mb-3 text-neutral-500">Services</div>
          <ul className="space-y-1.5 text-sm">
            {(settings?.services || []).slice(0, 5).map((sv, i) => (
              <li key={i}>{sv.title}</li>
            ))}
          </ul>
        </div>
        <div>
          <div className="overline mb-3 text-neutral-500">Company</div>
          <ul className="space-y-1.5 text-sm">
            <li><Link to="/request">Request a quote</Link></li>
            <li><Link to="/login">Sign in</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-black/10 py-4 text-center overline text-xs text-neutral-500">
        © {new Date().getFullYear()} NOSKO HANDYMAN CO. · {settings?.service_area || "DFW METROPLEX"}
      </div>
    </footer>
  );
}
