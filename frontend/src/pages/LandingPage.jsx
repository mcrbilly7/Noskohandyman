import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fileUrl } from "@/lib/api";
import Navbar from "@/components/shared/Navbar";
import Footer from "@/components/shared/Footer";
import { ArrowRight, Zap, Wrench, ShieldCheck, MapPin, CheckCircle2 } from "lucide-react";

const WORKER_IMG = "https://images.unsplash.com/photo-1772338537689-056082f100a9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNDR8MHwxfHNlYXJjaHwxfHxoYW5keW1hbiUyMHJlcGFpcmluZyUyMG91dGxldHxlbnwwfHx8fDE3NzkyMjQ1Njl8MA&ixlib=rb-4.1.0&q=85";
const TOOLS_IMG = "https://images.unsplash.com/photo-1584677191047-38f48d0db64e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwyfHxoYW5keW1hbiUyMHRvb2wlMjBib3h8ZW58MHx8fHwxNzc5MjI0NTgxfDA&ixlib=rb-4.1.0&q=85";
const HOUSE_IMG = "https://images.pexels.com/photos/7031622/pexels-photo-7031622.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

const STEP_ICONS = [Zap, Wrench, ShieldCheck];

export default function LandingPage() {
  const [s, setS] = useState(null);
  const [portfolio, setPortfolio] = useState([]);

  useEffect(() => {
    api.get("/site/settings").then((r) => setS(r.data)).catch(() => {});
    api.get("/portfolio").then((r) => setPortfolio(r.data || [])).catch(() => {});
  }, []);

  if (!s) {
    // Render with defaults so the page never hangs on a slow/failed settings call
    return (
      <div className="bg-white">
        <Navbar />
        <section className="border-b border-black/10">
          <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-20 lg:py-28">
            <div className="overline text-neutral-500">Loading content…</div>
            <h1 className="font-display text-5xl md:text-6xl tracking-tighter mt-3">Nosko Handyman</h1>
            <p className="mt-3 text-neutral-600">DFW Metroplex · Get a free quote in 24 hrs.</p>
            <Link to="/request" className="btn-brutal mt-6 inline-flex" data-testid="hero-request-btn">Get a free quote <ArrowRight className="w-4 h-4" /></Link>
          </div>
        </section>
        <Footer />
      </div>
    );
  }

  const minCharge = s.minimum_charge ?? 50;
  const outletPrice = s.outlet_price ?? 25;
  const servicesSub = s.services_subheading || `One known set price: $${outletPrice} per switch/outlet swap. Every visit has a $${minCharge} floor (covers travel + diagnosis). All other work gets a free quote.`;

  return (
    <div className="bg-white">
      <Navbar />

      {/* HERO */}
      <section className="border-b border-black/10">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-20 lg:py-28">
          <div className="grid lg:grid-cols-12 gap-12 items-center">
            <div className="lg:col-span-7">
              <div className="overline mb-6 flex items-center gap-3 text-neutral-600">
                <MapPin className="w-3 h-3" /> Serving the {s.service_area}
              </div>
              <h1 className="font-display text-5xl md:text-6xl lg:text-7xl leading-[1.02] tracking-tighter" data-testid="hero-title">
                {s.hero_title}
              </h1>
              <p className="mt-7 text-lg max-w-xl text-neutral-700" data-testid="hero-subtitle">
                {s.hero_subtitle}
              </p>
              <div className="mt-10 flex flex-wrap gap-3">
                <Link to="/request" className="btn-brutal" data-testid="hero-request-btn">
                  {s.cta_primary_label} <ArrowRight className="w-4 h-4" />
                </Link>
                <a href="#services" className="btn-brutal ghost" data-testid="hero-services-btn">{s.cta_secondary_label}</a>
              </div>
              <div className="mt-12 flex flex-wrap gap-x-8 gap-y-3 text-sm text-neutral-700">
                {["Licensed W9 handymen", "Upfront written quotes", "Photo confirmation"].map((t) => (
                  <span key={t} className="inline-flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-[#16A34A]" />{t}</span>
                ))}
              </div>
            </div>

            <div className="lg:col-span-5">
              <div className="border-2 border-black bg-white">
                <div className="grid grid-cols-2 divide-x-2 divide-black border-b-2 border-black">
                  <div className="p-6">
                    <div className="overline text-neutral-500">Per swap</div>
                    <div className="font-display text-5xl tracking-tighter mt-1">${outletPrice}</div>
                    <div className="overline mt-1">Switch / outlet</div>
                  </div>
                  <div className="p-6 bg-[#FFD600]">
                    <div className="overline">Visit minimum</div>
                    <div className="font-display text-5xl tracking-tighter mt-1">${minCharge}</div>
                    <div className="overline mt-1">On every job</div>
                  </div>
                </div>
                <div className="p-6">
                  <div className="overline text-neutral-500">All other work</div>
                  <div className="font-display text-2xl tracking-tight mt-1">Free quote in 24 hrs</div>
                  <p className="text-sm text-neutral-600 mt-2">Snap a photo, drop a description. We'll send back a fixed-price quote.</p>
                  <Link to="/request" className="btn-brutal dark w-full justify-center mt-5" data-testid="hero-quote-btn">
                    {s.cta_primary_label} <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SERVICES */}
      <section id="services" className="bg-[#F9FAFB] border-y border-black/10">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-20">
          <div className="overline text-neutral-500">{s.services_overline}</div>
          <h2 className="font-display text-4xl md:text-5xl tracking-tighter mt-2 max-w-3xl" data-testid="services-heading">
            {s.services_heading}
          </h2>
          <p className="mt-3 text-neutral-700 max-w-2xl">{servicesSub}</p>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-10">
            {(s.services || []).map((sv, i) => (
              <div key={i} className="border border-black bg-white p-5">
                <div className="font-display text-lg tracking-tight">{sv.title}</div>
                <p className="text-sm text-neutral-600 mt-1">{sv.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="max-w-[1280px] mx-auto px-6 lg:px-10 py-20">
        <div className="overline text-neutral-500">{s.how_overline}</div>
        <h2 className="font-display text-4xl md:text-5xl tracking-tighter mt-2" data-testid="how-heading">{s.how_heading}</h2>
        <div className="grid md:grid-cols-3 gap-6 mt-10">
          {(s.how_it_works || []).map((step, i) => {
            const Icon = STEP_ICONS[i] || Zap;
            return (
              <div key={i} className="border border-black bg-white p-7">
                <div className="flex items-center justify-between">
                  <Icon className="w-7 h-7" strokeWidth={2.5} />
                  <span className="num-badge">{String(i + 1).padStart(2, "0")}</span>
                </div>
                <div className="font-display text-2xl mt-5 tracking-tight">{step.title}</div>
                <p className="text-neutral-600 mt-2 text-sm">{step.description}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* PORTFOLIO */}
      <section className="bg-[#0A0A0A] text-white border-y border-black py-20">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div className="flex items-end justify-between flex-wrap gap-4">
            <div>
              <div className="overline text-[#FFD600]">Recent work</div>
              <h2 className="font-display text-4xl md:text-5xl tracking-tighter mt-2">From the toolbox.</h2>
            </div>
            <Link to="/request" className="btn-brutal" data-testid="portfolio-request-btn">Book yours <ArrowRight className="w-4 h-4" /></Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-10">
            {(portfolio.length > 0 ? portfolio : [
              { photo_id: "f1", title: "Outlet swap", _fallback: WORKER_IMG },
              { photo_id: "f2", title: "Garage shop", _fallback: TOOLS_IMG },
              { photo_id: "f3", title: "Home repair", _fallback: HOUSE_IMG },
              { photo_id: "f4", title: "Daily fix", _fallback: WORKER_IMG },
            ]).slice(0, 8).map((p) => (
              <div key={p.photo_id} className="aspect-square border border-white/20 overflow-hidden relative">
                <img src={p.storage_path ? fileUrl(p.storage_path) : p._fallback} alt={p.title} className="w-full h-full object-cover" />
                <div className="absolute bottom-0 left-0 right-0 bg-black/70 p-2 overline text-xs text-[#FFD600]">{p.title}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-[#0A0A0A] text-white">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-16 flex flex-wrap items-center justify-between gap-6">
          <div>
            <div className="overline text-[#FFD600]">{s.final_cta_overline}</div>
            <h3 className="font-display text-3xl md:text-4xl tracking-tighter mt-2">{s.final_cta_heading}</h3>
          </div>
          <Link to="/request" className="btn-brutal" data-testid="cta-request-btn">{s.final_cta_label} <ArrowRight className="w-4 h-4" /></Link>
        </div>
      </section>

      <Footer settings={s} />
    </div>
  );
}
