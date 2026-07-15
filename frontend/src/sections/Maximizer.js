import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { QrCode, Gift, Crown, Clock, ExternalLink, Gamepad2, Upload, Video, Send } from "lucide-react";
import {
  getSegments, getDrip, spin, getGames, setActiveGame,
  getSampleCustomerCsv, importCustomerCsv, getWelcomeQueue, sendWelcome,
} from "@/lib/api";
import { SectionTitle, Overline } from "@/components/ui-bits";
import Codes from "@/sections/Codes";

const segColor = { vip: "#27AE60", standard: "#5C5A56", promo_pool: "#F39C12" };
const segLabel = { vip: "VIP", standard: "Standard", promo_pool: "Promo Pool" };
const custSegColor = { new: "#2980B9", coupon_only: "#F39C12", loyal: "#27AE60" };
const custSegLabel = { new: "New Customer", coupon_only: "Coupon-Only", loyal: "Loyal" };

const GUEST_OPTIONS = [
  { key: "new", seg: "new", isNew: true, label: "New Guest", hint: "80% win big — entice them in" },
  { key: "vip", seg: "vip", isNew: false, label: "Quality Regular", hint: "High reward — reward loyalty" },
  { key: "promo_pool", seg: "promo_pool", isNew: false, label: "Couponer", hint: "Small reward — protect margin" },
];

export default function Maximizer() {
  const [segments, setSegments] = useState(null);
  const [drip, setDrip] = useState(null);
  const [games, setGames] = useState(null);
  const [result, setResult] = useState(null);
  const [spinning, setSpinning] = useState(false);
  const [guest, setGuest] = useState(GUEST_OPTIONS[0]);
  const [csv, setCsv] = useState("");
  const [importRes, setImportRes] = useState(null);
  const [welcome, setWelcome] = useState(null);

  const loadWelcome = () => getWelcomeQueue().then(setWelcome).catch(() => {});
  useEffect(() => {
    getSegments().then(setSegments).catch(() => {});
    getDrip().then(setDrip).catch(() => {});
    getGames().then(setGames).catch(() => {});
    loadWelcome();
  }, []);

  const chooseGame = async (id) => {
    const res = await setActiveGame(id);
    setGames((g) => ({ ...g, active: res.active, override: res.override }));
    toast.success(`Active game set: ${res.active.name}`);
  };

  const doSpin = async () => {
    setSpinning(true); setResult(null);
    setTimeout(async () => {
      const res = await spin(guest.isNew, guest.seg);
      setResult(res); setSpinning(false);
      toast[res.tier === "highValue" ? "success" : "message"](`${guest.label} won: ${res.reward}`,
        { description: `Coupon ${res.couponCode} auto-applies at checkout` });
    }, 700);
  };

  const loadSampleCustomers = async () => { const { csv } = await getSampleCustomerCsv(); setCsv(csv); toast("Weekly customer export loaded"); };
  const runImport = async () => {
    const r = await importCustomerCsv(csv);
    setImportRes(r); await loadWelcome();
    toast.success(`Imported ${r.imported} — ${r.newCustomersQueued} new customers queued for welcome video`);
  };
  const triggerWelcome = async (i) => {
    const r = await sendWelcome(i);
    await loadWelcome();
    toast.success("Welcome video email triggered", { description: `Mode: ${r.result.status} · headers: ${Object.keys(r.result.headers || {}).join(", ")}` });
  };

  if (!segments || !drip || !games) return <div className="p-10" style={{ color: "var(--text-secondary)" }}>Loading…</div>;

  return (
    <div className="p-6 md:p-12 max-w-[1200px]">
      <SectionTitle kicker="Rewards · Quality Customer Maximizer"
        title="Turn the click into a customer — and prove the order"
        subtitle="Four rotating games keep it fresh, weekly CSV imports segment your customers, new customers get a personal welcome video, and every coupon flows back so OmniLocal #1 knows the ad made real money." />

      {/* Four rotating games */}
      <div className="card p-6 md:p-8" data-testid="games-module">
        <div className="flex items-center gap-2"><Gamepad2 size={18} color="var(--primary)" /><Overline>Four Rotating Games · new one every 30 days</Overline></div>
        <h3 className="serif text-2xl mt-1">Active game: {games.active.name}</h3>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          Rotates automatically on a 30-day cycle so returning customers always find something fresh — or pin one below (admin override, no redeploy).
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          {games.games.map((g) => {
            const on = games.active.id === g.id;
            return (
              <button key={g.id} onClick={() => chooseGame(g.id)} data-testid={`game-${g.id}`}
                className="text-left p-4 rounded-lg lift"
                style={{ border: on ? "2px solid var(--primary)" : "1px solid var(--border)",
                         background: on ? "var(--surface-alt)" : "transparent" }}>
                <div className="font-bold text-sm">{g.name}</div>
                <div className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>{g.tagline}</div>
                {on && <div className="overline mt-2" style={{ color: "var(--primary)", fontSize: "0.5rem" }}>● Active ({games.active.source === "admin_override" ? "pinned" : "auto"})</div>}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        {/* Scan to Spin */}
        <div className="card p-6 md:p-8" data-testid="scan-to-spin">
          <div className="flex items-center gap-2"><QrCode size={18} color="var(--primary)" /><Overline>{games.active.name}</Overline></div>
          <h3 className="serif text-2xl mt-1">Segment-aware rewards</h3>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            New & quality guests win the big reward to entice them in — couponers get something small to protect your margin.
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
              {spinning ? "Playing…" : `Play · ${guest.label}`}
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

        {/* Drip */}
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

      {/* Weekly CSV import + segmentation */}
      <div className="card p-6 md:p-8 mt-8" data-testid="csv-import">
        <div className="flex items-center gap-2"><Upload size={18} color="var(--primary)" /><Overline>Weekly Customer Import · segmentation</Overline></div>
        <h3 className="serif text-2xl mt-1">Download your customer CSV weekly, drop it here</h3>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          Do it during your normal inventory/payroll routine. We auto-sort everyone into coupon-only, loyal, and new —
          and new customers trigger the welcome video below.
        </p>
        <textarea data-testid="customer-csv-input" value={csv} onChange={(e) => setCsv(e.target.value)} rows={4}
          placeholder="name,email,visits,coupon_ratio" className="w-full mt-3 p-3 rounded-lg mono text-sm"
          style={{ border: "1px solid var(--border)", background: "var(--surface)", resize: "vertical" }} />
        <div className="flex gap-2 mt-3">
          <button className="btn btn-ghost" onClick={loadSampleCustomers} data-testid="load-customers-btn">Load Sample Export</button>
          <button className="btn btn-primary" disabled={!csv.trim()} onClick={runImport} data-testid="import-customers-btn">Import & Segment</button>
        </div>
        {importRes && (
          <div className="mt-5" data-testid="import-result">
            <div className="flex flex-wrap gap-3">
              {Object.entries(importRes.segments).map(([k, v]) => (
                <div key={k} className="px-4 py-2 rounded-lg" style={{ background: "var(--surface-alt)" }}>
                  <span className="text-xs font-bold px-2 py-0.5 rounded mr-2" style={{ color: "#fff", background: custSegColor[k] }}>{custSegLabel[k]}</span>
                  <span className="mono text-lg">{v}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Welcome video automation */}
      {welcome && (
        <div className="card p-6 md:p-8 mt-8" data-testid="welcome-automation">
          <div className="flex items-center gap-2"><Video size={18} color="var(--success)" /><Overline>New Customer Welcome · automated owner video</Overline></div>
          <h3 className="serif text-2xl mt-1">A 7-second personal thank-you, within hours of enrollment</h3>
          <div className="mt-3 p-4 rounded-lg" style={{ background: "var(--surface-alt)" }}>
            <div className="text-xs" style={{ color: "var(--text-secondary)" }}>Owner video (single pre-recorded clip, delivered by email):</div>
            <a href={welcome.ownerVideoUrl} target="_blank" rel="noreferrer" className="mono text-xs" style={{ color: "var(--primary)" }}>{welcome.ownerVideoUrl}</a>
            <p className="text-sm mt-2 italic">"{welcome.script}"</p>
          </div>
          <div className="mt-4">
            <Overline>Welcome Queue ({welcome.queue.length})</Overline>
            {welcome.queue.length === 0 && <p className="text-sm mt-2" style={{ color: "var(--text-secondary)" }}>No new customers yet — import a CSV above to populate.</p>}
            <div className="mt-2 space-y-2">
              {welcome.queue.slice(0, 8).map((q, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg" style={{ border: "1px solid var(--border)" }} data-testid={`welcome-item-${i}`}>
                  <div>
                    <div className="font-semibold text-sm">{q.name}</div>
                    <div className="text-xs mono" style={{ color: "var(--text-secondary)" }}>{q.email} · {q.status}</div>
                  </div>
                  <button className="btn btn-ghost" style={{ padding: "0.4rem 0.9rem" }} onClick={() => triggerWelcome(i)} data-testid={`send-welcome-${i}`}>
                    <Send size={13} className="inline mr-1" /> {q.status === "sent" ? "Resend" : "Send Video"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

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
                <th className="text-left py-2">Customer</th><th className="text-right py-2">Visits</th>
                <th className="text-right py-2">Avg Ticket</th><th className="text-right py-2">Score</th>
                <th className="text-left py-2 pl-4">Segment</th>
              </tr>
            </thead>
            <tbody>
              {segments.rows.map((r) => (
                <tr key={r.customerId} style={{ borderBottom: "1px solid var(--border)", background: r.segment === "vip" ? "#f1f8f3" : "transparent" }} data-testid={`cust-${r.customerId}`}>
                  <td className="py-2 font-semibold">{r.name}</td>
                  <td className="py-2 text-right mono">{r.frequency}</td>
                  <td className="py-2 text-right mono">${r.avgTicket.toFixed(2)}</td>
                  <td className="py-2 text-right mono">{r.score.toFixed(2)}</td>
                  <td className="py-2 pl-4"><span className="text-xs font-bold px-2 py-0.5 rounded" style={{ color: "#fff", background: segColor[r.segment] }}>{segLabel[r.segment]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* POS Verification */}
      <div className="card p-6 md:p-8 mt-8" data-testid="verification">
        <Overline>POS Verification · from CSV / ordering platform</Overline>
        <h3 className="serif text-2xl mt-1">The proof it worked — and who's worth chasing</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <div><Overline>Codes Issued</Overline><div className="mono text-2xl">{segments.verification.codesIssued}</div></div>
          <div><Overline>Codes Redeemed</Overline><div className="mono text-2xl" style={{ color: "var(--primary)" }}>{segments.verification.codesRedeemed}</div></div>
          <div><Overline>Redemption Rate</Overline><div className="mono text-2xl">{(segments.verification.redemptionRate * 100).toFixed(0)}%</div></div>
          <div><Overline>Revenue Proven</Overline><div className="mono text-2xl" style={{ color: "var(--success)" }}>${segments.verification.revenueFromRedemptions.toLocaleString()}</div></div>
        </div>
        <p className="text-sm mt-4" style={{ color: "var(--text-secondary)" }}>{segments.verification.note}</p>
      </div>

      {/* Codes & Redemption folded in */}
      <div className="mt-4"><Codes /></div>
    </div>
  );
}
