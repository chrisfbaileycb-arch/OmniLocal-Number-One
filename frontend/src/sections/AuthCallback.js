import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { authSession } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
  const hasProcessed = useRef(false);
  const navigate = useNavigate();
  const { apply } = useAuth();

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;
    const sessionId = new URLSearchParams(window.location.hash.slice(1)).get("session_id");
    (async () => {
      try {
        const d = await authSession(sessionId);
        window.history.replaceState(null, "", "/");
        apply(d);
        navigate("/", { replace: true });
      } catch {
        window.history.replaceState(null, "", "/");
        window.location.reload();
      }
    })();
  }, [apply, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bone)" }}>
      <div className="overline" data-testid="auth-callback-loading" style={{ color: "var(--text-secondary)" }}>
        Signing you in…
      </div>
    </div>
  );
}
