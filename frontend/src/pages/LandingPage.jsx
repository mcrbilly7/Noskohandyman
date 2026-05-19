import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, fileUrl } from "@/lib/api";
import Navbar from "@/components/shared/Navbar";
import Footer from "@/components/shared/Footer";
import { ArrowRight, Zap, Wrench, ShieldCheck, BadgeDollarSign, MapPin } from "lucide-react";

const HERO_BG = "https://static.prod-images.emergentagent.com/jobs/5522244e-207c-4884-a8ae-8054cebf7d37/images/9237dd3c40539c2efaf48c028820ab8d9ed683bda0ca92aae6f1db3253e6838f.png";
const WORKER_IMG = "https://images.unsplash.com/photo-1772338537689-056082f100a9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNDR8MHwxfHNlYXJjaHwxfHxoYW5keW1hbiUyMHJlcGFpcmluZyUyMG91dGxldHxlbnwwfHx8fDE3NzkyMjQ1Njl8MA&ixlib=rb-4.1.0&q=85";
const HOUSE_IMG = "https://images.pexels.com/photos/7031622/pexels-photo-7031622.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";
const TOOLS_IMG = "https://images.unsplash.com/photo-1584677191047-38f48d0db64e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwyfHxoYW5keW1hbiUyMHRvb2wlMjBib3h8ZW58MHx8fHwxNzc5MjI0NTgxfDA&ixlib=rb-4.1.0&q=85";

export default function LandingPage() {
  const [settings, setSettings] = useState(null);
  const [portfolio, setPortfolio] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/site/settings").then((r) => setSettings(r.data)).catch(() => {});
    api.get("/portfolio").then((r) => setPortfolio(r.data || [])).catch(() => {});
  }, []);

  return (
    <div className="bg-white">
      <Navbar />

      {/* HERO */}
      <section className="border-b-2 border-black">
        <div className="max-w-[1400px] mx-auto grid lg:grid-cols-12 gap-0">
          <div className="lg:col-span-7 px-6 lg:px-10 py-12 lg:py-20 border-r-0 lg:border-r-2 border-black">
            <div className="overline mb-6 inline-flex items-center gap-2">
              <span className="num-badge">01</span>
              <span>W9 / 1099 — LICENSED HANDYMAN NETWORK</span>
            </div>
            <h1 className="font-display text-5xl md:text-6xl lg:text-7xl leading-[0.95] tracking-tighter">
              {settings?.hero_title || "Fast, fair,"}<br />
              <span className="bg-[#FFD600] px-2 inline-block">fixed-price</span> repairs.
            </h1>
            <p className="mt-6 text-lg max-w-xl text-neutral-700">
              {settings?.hero_subtitle || "Switch or outlet replacement starting at $25. $25 minimum on every job. No mystery line items, no upcharge games."}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/request" className="btn-brutal" data-testid="hero-request-btn">
                Book a job <ArrowRight className="w-4 h-4" />
              </Link>
              <Link to="/join/worker" className="btn-brutal ghost" data-testid="hero-worker-btn">
                Become a handyman
              </Link>
              <Link to="/join/marketer" className="btn-brutal ghost" data-testid="hero-marketer-btn">
                Marketer program · 15%
              </Link>
            </div>

            {/* Price card */}
            <div className="mt-12 grid sm:grid-cols-2 gap-0 border border-black">
              <div className="grid-box-yellow p-6 border-r border-black">
                <div className="overline">Set price</div>
                <div className="font-display text-6xl tracking-tighter mt-1">$25</div>
                <div className="overline mt-1">Switch / Outlet replacement</div>
              </div>
              <div className="grid-box p-6">
                <div className="overline">Minimum</div>
                <div className="font-display text-6xl tracking-tighter mt-1">$25</div>
                <div className="overline mt-1">On every job — no exceptions</div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-5 relative min-h-[420px]" style={{
            backgroundImage: `url(${HERO_BG})`, backgroundSize: "cover", backgroundPosition: "center"
          }}>
            <div className="absolute inset-0 bg-black/10" />
            <div className="absolute bottom-6 left-6 right-6">
              <div className="grid-box-dark p-5">
                <div className="overline text-[#FFD600]">Service area</div>
                <div className="font-display text-2xl mt-1 flex items-center gap-2">
                  <MapPin className="w-5 h-5 text-[#FFD600]" /> {settings?.service_area || "Greater Metro Area"}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Marquee */}
      <div className="marquee">
        <div className="marquee-track">
          {Array.from({ length: 2 }).map((_, k) => (
            <span key={k}>
              ⚡ FAST REPAIRS · $25 SET PRICE · $25 MINIMUM · W9 WORKERS · 15% MARKETER PROFIT SHARE · UPLOAD A PHOTO, GET A QUOTE · ⚡ &nbsp;&nbsp;&nbsp;&nbsp;
            </span>
          ))}
        </div>
      </div>

      {/* HOW IT WORKS */}
      <section className="max-w-[1400px] mx-auto px-6 py-20">
        <div className="overline mb-3">How it works</div>
        <h2 className="font-display text-4xl md:text-5xl tracking-tighter max-w-2xl">
          Three steps. Zero phone tag.
        </h2>
        <div className="grid md:grid-cols-3 gap-0 mt-10 border border-black">
          {[
            { n: "01", t: "Snap a photo", d: "Upload a picture of the switch, outlet, or job. Add the address.", icon: Zap },
            { n: "02", t: "We dispatch", d: "A W9-compliant handyman in your area accepts the job.", icon: Wrench },
            { n: "03", t: "Fixed-price done", d: "$25 set price. $25 minimum. Pay when complete — no surprises.", icon: ShieldCheck },
          ].map((s) => (
            <div key={s.n} className="p-8 border-r border-black last:border-r-0">
              <div className="num-badge mb-4">{s.n}</div>
              <s.icon className="w-8 h-8" strokeWidth={2.5} />
              <div className="font-display text-2xl mt-4 tracking-tight">{s.t}</div>
              <p className="text-neutral-600 mt-2">{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* PORTFOLIO */}
      <section className="bg-[#0A0A0A] text-white border-y-2 border-black py-20">
        <div className="max-w-[1400px] mx-auto px-6">
          <div className="flex items-end justify-between flex-wrap gap-4">
            <div>
              <div className="overline text-[#FFD600]">Recent work</div>
              <h2 className="font-display text-4xl md:text-5xl tracking-tighter mt-2">From the toolbox.</h2>
            </div>
            <Link to="/request" className="btn-brutal" data-testid="portfolio-request-btn">Book yours <ArrowRight className="w-4 h-4" /></Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-10">
            {(portfolio.length > 0 ? portfolio : [
              { photo_id: "f1", title: "Outlet swap", storage_path: null, _fallback: WORKER_IMG },
              { photo_id: "f2", title: "Garage tools", storage_path: null, _fallback: TOOLS_IMG },
              { photo_id: "f3", title: "Modern home", storage_path: null, _fallback: HOUSE_IMG },
              { photo_id: "f4", title: "Daily fix", storage_path: null, _fallback: WORKER_IMG },
            ]).slice(0, 8).map((p) => (
              <div key={p.photo_id} className="aspect-square border border-white/20 overflow-hidden relative">
                <img
                  src={p.storage_path ? fileUrl(p.storage_path) : p._fallback}
                  alt={p.title}
                  className="w-full h-full object-cover"
                />
                <div className="absolute bottom-0 left-0 right-0 bg-black/70 p-2 overline text-xs text-[#FFD600]">{p.title}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* PROGRAMS */}
      <section className="max-w-[1400px] mx-auto px-6 py-20 grid md:grid-cols-2 gap-0 border border-black">
        <div className="p-10 border-r border-black bg-white">
          <BadgeDollarSign className="w-10 h-10" />
          <h3 className="font-display text-3xl mt-4 tracking-tighter">Marketer program — 15% share</h3>
          <p className="text-neutral-700 mt-3">
            Sign up, get a personal referral code. Anyone who books using your code earns you a 15% profit share — paid weekly.
          </p>
          <Link to="/join/marketer" className="btn-brutal mt-6 inline-flex" data-testid="program-marketer-btn">
            Join as marketer <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="p-10 grid-box-yellow">
          <Wrench className="w-10 h-10" />
          <h3 className="font-display text-3xl mt-4 tracking-tighter">Handymen wanted</h3>
          <p className="mt-3">
            Set your hours. Pick your skills. Get paid via the app. W9 / 1099 with full earnings dashboard.
          </p>
          <Link to="/join/worker" className="btn-brutal dark mt-6 inline-flex" data-testid="program-worker-btn">
            Apply as handyman <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
}
