import React, { useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { api } from "@/lib/api";

export default function AuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;
    const hash = location.hash || window.location.hash;
    const params = new URLSearchParams(hash.replace(/^#/, ""));
    const sessionId = params.get("session_id");
    if (!sessionId) {
      navigate("/", { replace: true });
      return;
    }
    (async () => {
      try {
        const res = await api.post("/auth/session", { session_id: sessionId });
        if (res.data?.session_token) {
          localStorage.setItem("nosko_session_token", res.data.session_token);
        }
        const u = res.data?.user;
        const dest = u?.role === "admin" ? "/admin" :
                     u?.role === "worker" ? "/dashboard/worker" :
                     u?.role === "marketer" ? "/dashboard/marketer" : "/dashboard";
        navigate(dest, { replace: true, state: { user: u } });
      } catch (e) {
        navigate("/", { replace: true });
      }
    })();
  }, [location, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-white">
      <div className="overline">Authenticating…</div>
    </div>
  );
}
