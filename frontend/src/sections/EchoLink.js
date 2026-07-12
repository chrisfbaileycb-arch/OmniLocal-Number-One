import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { QrCode, Gift, Crown, Clock, ExternalLink } from "lucide-react";
import { getSegments, getDrip, spin } from "@/lib/api";
import { SectionTitle, Overline } from "@/components/ui-bits";

const segColor = { vip: "#27AE60", standard: "#5C5A56", promo_pool: "#F39C12" };
const segLabel = { vip: "VIP", standard: "Standard", promo_pool: "Promo Pool" };

const GUEST_OPTIONS = [
  { key: "new", seg: "new", isNew: true, label: "New Guest", hint: "80% win big — entice them in" },
  { key: "vip", seg: "vip", isNew: false, label: "Quality Regular", hint: "High reward — reward loyalty" },
  { key: "promo_pool", seg: "promo_pool", isNew: false, label: "Couponer", hint: "Small reward — protect margin" },
];

export default function EchoLink() {
  const [segments, setSegments] = useState(null);
  const [drip, setDrip] = useState(null);
  const [result, setResult] = useState(null);
  const [spinning, setSpinning] = useState(false);
  const [guest, setGuest] = useState(GUEST_OPTIONS[0]);

  useEffect(() => {
    getSegments().then(setSegments).catch(() => {});
    getDrip().then(setDrip).catch(() => {});
  }, []);

  const doSpin = async () => {
    setSpinning(true);
    setResult(null);
    setTimeout(async () => {
      const res = await spin(guest.isNew, guest.seg);
      setResult(res);
      setSpinning(false);
      toast[res.tier === "highValue" ? "success" : "message"](
        `${guest.label} won: ${res.reward}`,
        { description: `Coupon ${res.couponCode} auto-applies at checkout` }
      );
    }, 700);
  };

  if (!segments || !drip) return <div className="p-10" style={{ color: "var(--text-secondary)" }}>Loading…</div>;

  return (
    <div className="p-6 md:p-12 max-w-[1200px]">
      <SectionTitle kicker="Module 03 · EchoLink"
        title="Turn the click into a customer — and prove the order"
        subtitle="Every ad's button lands here. Guests scan-to-spin, the coupon auto-applies at the ordering platform, and the promo code flows back so AdSmith knows that ad made real money. This is how clicks become revenue." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Scan to Spin */}
        <div className="card p-6 md:p-8" data-testid="scan-to-spin">
          <div className="flex items-center gap-2"><QrCode size={18} color="var(--primary)" /><Overline>Scan-to-Spin</Overline></div>
          <h3 className="serif text-2xl mt-1">Gamified guest acquisition</h3>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            Rewards are segment-aware: new & quality guests win the big reward to entice them in — couponers get something small to protect your margin.
          </p>

          <div className="grid place-items-center my-6">
            <motion.div animate={{ rotate: spinning ? 720 : 0 }} transition={{ duration: 0.7, ease: "easeOut" }}
              className="grid place-items-center rounded-full"
              style={{ width: 150, height: 150, background: "conic-gradient(#D35400 0 25%, #27AE60 25% 50%, #F39C12 50% 75%, #2980B9 75% 100%)" }}>
              <div className="grid place-items-center rounded-full" style={{ width: 108, height: 108, background: "var(--surface)" }}>
                <Gift size={40} color="var(--primary)" />
              </div>
            </motion.div>
          </div>

          <div className="flex flex-col gap-2 mb-4">
            {GUEST_OPTIONS.map((g) => (
              <button key={g.key} onClick={() => { setGuest(g); setResult(null); }} data-testid={`guest-${g.key}`}
                className="text-left px-3 py-2 rounded-lg"
                style={{ border: guest.key === g.key ? "2px solid var(--primary)" : "1px solid var(--border)",
                         background: guest.key === g.key ? "var(--surface-alt)" : "transparent" }}>
                <div className="text-sm font-bold">{g.label}</div>
                <div className="text-xs" style={{ color: "var(--text-secondary)" }}>{g.hint}</div>
              </button>
            ))}
          </div>

          <div className="flex justify-center">
            <button className="btn btn-primary" onClick={doSpin} disabled={spinning} data-testid="spin-btn">
              {spinning ? "Spinning…" : `Spin the Wheel · ${guest.label}`}
            </button>
          </div>

          {result && (
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="mt-6 p-5 rounded-lg text-center" style={{ background: "var(--surface-alt)" }} data-testid="spin-result">
              <Overline style={{ color: result.tier === "highValue" ? "var(--success)" : "var(--text-secondary)" }}>
                {result.tier === "highValue" ? "High-Value Reward" : "Standard Reward"}
              </Overline>
              <div className="serif text-3xl mt-1">{result.reward}</div>
              <div className="mono text-sm mt-2" style={{ color: "var(--primary)" }}>{result.couponCode}</div>
              <div className="flex items-center justify-center gap-1 text-xs mt-3" style={{ color: "var(--text-secondary)" }}>
                <ExternalLink size={12} /> Auto-applies at Toast / Heartland / DoorDash checkout
              </div>
            </motion.div>
          )}
        </div>

        {/* Drip timeline */}
        <div className="card p-6 md:p-8" data-testid="drip-campaign">
          <div className="flex items-center gap-2"><Clock size={18} color="var(--info)" /><Overline>Slow-Trickle Drip</Overline></div>
          <h3 className="serif text-2xl mt-1">30-day watch-to-unlock campaign</h3>
          <div className="grid grid-cols-3 gap-3 mt-4">
            <div><Overline>Total Leads</Overline><div className="mono text-2xl">{drip.totalLeads}</div></div>
            <div><Overline>Released</Overline><div className="mono text-2xl" style={{ color: "var(--success)" }}>{drip.releasedSoFar}</div></div>
            <div><Overline>Per Day</Overline><div className="mono text-2xl">{drip.dailyRate}</div></div>
          </div>
          <div className="mt-5">
            <div className="flex justify-between text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
              <span>Day 12 of {drip.days}</span><span>{drip.remaining} remaining</span>
            </div>
            <div className="h-3 rounded-full" style={{ background: "var(--surface-alt)" }}>
              <motion.div initial={{ width: 0 }} animate={{ width: `${(drip.releasedSoFar / drip.totalLeads) * 100}%` }}
                transition={{ duration: 0.8 }} className="h-3 rounded-full" style={{ background: "var(--info)" }} />
            </div>
          </div>
          <p className="text-sm mt-5" style={{ color: "var(--text-secondary)" }}>
            Leads release at a steady daily pace — each gets a watch-to-unlock video revealing a coupon at {drip.revealAtSeconds}s.
            Steady drip keeps the pipeline warm without burning the list.
          </p>
        </div>
      </div>

      {/* RFMD segments */}
      <div className="card p-6 md:p-8 mt-8">
        <div className="flex items-center gap-2"><Crown size={18} color="var(--success)" /><Overline>RFMD VIP Segmenting</Overline></div>
        <h3 className="serif text-2xl mt-1">Know exactly who your VIPs are</h3>
        <div className="flex gap-4 mt-2 mb-4 text-sm">
          {Object.entries(segments.counts).map(([k, v]) => (
            <span key={k} className="flex items-center gap-1">
              <span style={{ width: 10, height: 10, borderRadius: 999, background: segColor[k], display: "inline-block" }} />
              {segLabel[k]}: <b>{v}</b>
            </span>
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="rfmd-table">
            <thead>
              <tr className="overline" style={{ borderBottom: "1px solid var(--border)" }}>
                <th className="text-left py-2">Customer</th>
                <th className="text-right py-2">Visits</th>
                <th className="text-right py-2">Avg Ticket</th>
                <th className="text-right py-2">Score</th>
                <th className="text-left py-2 pl-4">Segment</th>
              </tr>
            </thead>
            <tbody>
              {segments.rows.map((r) => (
                <tr key={r.customerId} style={{ borderBottom: "1px solid var(--border)",
                  background: r.segment === "vip" ? "#f1f8f3" : "transparent" }} data-testid={`cust-${r.customerId}`}>
                  <td className="py-2 font-semibold">{r.name}</td>
                  <td className="py-2 text-right mono">{r.frequency}</td>
                  <td className="py-2 text-right mono">${r.avgTicket.toFixed(2)}</td>
                  <td className="py-2 text-right mono">{r.score.toFixed(2)}</td>
                  <td className="py-2 pl-4">
                    <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ color: "#fff", background: segColor[r.segment] }}>
                      {segLabel[r.segment]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* POS Verification — the proof it worked */}
      <div className="card p-6 md:p-8 mt-8" data-testid="verification">
        <Overline>POS Verification · from CSV / ordering platform</Overline>
        <h3 className="serif text-2xl mt-1">The proof it worked — and who's worth chasing</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <div><Overline>Codes Issued</Overline><div className="mono text-2xl">{segments.verification.codesIssued}</div></div>
          <div><Overline>Codes Redeemed</Overline><div className="mono text-2xl" style={{ color: "var(--primary)" }}>{segments.verification.codesRedeemed}</div></div>
          <div><Overline>Redemption Rate</Overline><div className="mono text-2xl">{(segments.verification.redemptionRate * 100).toFixed(0)}%</div></div>
          <div><Overline>Revenue Proven</Overline><div className="mono text-2xl" style={{ color: "var(--success)" }}>${segments.verification.revenueFromRedemptions.toLocaleString()}</div></div>
        </div>
        <div className="grid grid-cols-2 gap-3 mt-4">
          <div className="p-3 rounded-lg" style={{ border: "1px solid var(--border)" }}>
            <div className="text-xs" style={{ color: "var(--text-secondary)" }}>Margin-eroding couponers</div>
            <div className="mono text-xl" style={{ color: "#F39C12" }}>{segments.verification.couponers}</div>
          </div>
          <div className="p-3 rounded-lg" style={{ border: "1px solid var(--border)" }}>
            <div className="text-xs" style={{ color: "var(--text-secondary)" }}>High-value regulars</div>
            <div className="mono text-xl" style={{ color: "var(--success)" }}>{segments.verification.qualityCustomers}</div>
          </div>
        </div>
        <p className="text-sm mt-4" style={{ color: "var(--text-secondary)" }}>{segments.verification.note}</p>
      </div>
    </div>
  );
}
