import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Facebook, Instagram, MapPin, Music2, Youtube, Check, Info, Video } from "lucide-react";
import { getConnections, setConnection } from "@/lib/api";
import { SectionTitle, Overline } from "@/components/ui-bits";

const ICONS = {
  facebook: Facebook, instagram: Instagram, google: MapPin, tiktok: Music2, youtube: Youtube,
};

const SETUP_HINTS = {
  tiktok: "Create a TikTok Business account + link a page before the call.",
  youtube: "Set up a YouTube channel; enable Shorts.",
  instagram: "Convert to a Professional (Business) account and link your Facebook Page.",
  facebook: "Create a Facebook Business Page (not just a profile).",
  google: "Claim your Google Business Profile and verify the listing.",
};

export default function Connections() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = () => getConnections().then(setData).catch(() => {});
  useEffect(() => { load(); }, []);

  const toggle = async (platform, connected) => {
    setBusy(platform);
    try {
      const res = await setConnection(platform, connected);
      setData(res);
      toast[connected ? "success" : "message"](
        `${platform} ${connected ? "connected" : "disconnected"}`,
        { description: connected ? "the Ad Engine can now allocate budget here." : "the Ad Engine will stop recommending this channel." }
      );
    } finally { setBusy(null); }
  };

  if (!data) return <div className="p-10" style={{ color: "var(--text-secondary)" }}>Loading…</div>;
  const count = data.connectedCount;

  return (
    <div className="p-6 md:p-12 max-w-[1200px]">
      <SectionTitle kicker="Onboarding · Connections"
        title="Connect your platforms — the Ad Engine only spends where you're present"
        subtitle="Toggle on the channels you actually have. the Ad Engine will never recommend a platform you're not connected to. Connect 3–4 for the widest reach." />

      <div className="card p-5 mb-6 flex items-start gap-3" style={{ background: "var(--surface-alt)" }} data-testid="diversification-banner">
        <Info size={18} color="var(--primary)" className="mt-0.5" />
        <div>
          <div className="font-bold text-sm">You have {count} platform{count === 1 ? "" : "s"} connected.</div>
          <div className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {count < 3
              ? "People are creatures of habit — ~80% live on a single platform. Connecting 3–4 lets the Ad Engine reach audiences you'd otherwise miss. It still works with one, but more diversity = wider, more effective outreach."
              : "Great — enough diversity for the Ad Engine to spread spend across habit-locked audiences for maximum reach."}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.platforms.map((p) => {
          const Icon = ICONS[p.id] || Video;
          return (
            <div key={p.id} className="card p-5 flex items-center justify-between lift"
              data-testid={`platform-${p.id}`}
              style={{ borderColor: p.connected ? "var(--success)" : "var(--border)", borderWidth: p.connected ? 2 : 1 }}>
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-lg grid place-items-center"
                  style={{ background: p.connected ? "var(--success)" : "var(--surface-alt)" }}>
                  <Icon size={20} color={p.connected ? "#fff" : "var(--text-secondary)"} />
                </div>
                <div>
                  <div className="font-bold">{p.label}</div>
                  <div className="text-xs" style={{ color: "var(--text-secondary)" }}>
                    {p.connected ? <span style={{ color: "var(--success)" }}><Check size={11} className="inline" /> Connected</span> : SETUP_HINTS[p.id]}
                  </div>
                </div>
              </div>
              <button
                data-testid={`toggle-${p.id}`}
                disabled={busy === p.id}
                onClick={() => toggle(p.id, !p.connected)}
                className="relative rounded-full transition-colors"
                style={{ width: 48, height: 26, background: p.connected ? "var(--success)" : "#cfccc4" }}>
                <span className="absolute rounded-full bg-white transition-transform"
                  style={{ width: 20, height: 20, top: 3, left: 3, transform: p.connected ? "translateX(22px)" : "translateX(0)" }} />
              </button>
            </div>
          );
        })}
      </div>

      <div className="card p-6 md:p-8 mt-8" data-testid="zoom-prep">
        <Overline style={{ color: "var(--primary)" }}>Before your onboarding Zoom</Overline>
        <h3 className="serif text-2xl mt-1">Make the call efficient — set these up first</h3>
        <p className="text-sm mt-2" style={{ color: "var(--text-secondary)" }}>
          Send new restaurants this prep list so call time isn't spent creating accounts. On the call, we just toggle on
          what's ready and connect them in minutes.
        </p>
        <ul className="mt-4 space-y-2 text-sm">
          {data.platforms.filter((p) => !p.connected).map((p) => (
            <li key={p.id} className="flex gap-2"><span style={{ color: "var(--primary)" }}>→</span> <b>{p.label}:</b> {SETUP_HINTS[p.id]}</li>
          ))}
          {data.platforms.every((p) => p.connected) && <li style={{ color: "var(--success)" }}>All platforms connected — you're fully set up!</li>}
        </ul>
      </div>
    </div>
  );
}
