import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import { Trophy, Play, RotateCcw, MapPin, Plug } from "lucide-react";
import { getReports, reconcile, resetLoop, getRecommendedPlan } from "@/lib/api";
import { SectionTitle, Overline, usd } from "@/components/ui-bits";

function StrategyCard({ strat, alloc, metrics, labels, isWinner }) {
  return (
    <div className="card p-6 lift" data-testid={`strategy-${strat.id}`}
      style={{ borderColor: isWinner ? "var(--success)" : "var(--border)", borderWidth: isWinner ? 2 : 1 }}>
      <div className="flex items-center justify-between">
        <div>
          <Overline>Strategy {strat.id}</Overline>
          <h3 className="serif text-2xl">{strat.displayName}</h3>
        </div>
        {isWinner && (
          <span className="flex items-center gap-1 text-xs font-bold px-3 py-1 rounded-full"
            style={{ background: "var(--success)", color: "#fff" }} data-testid={`winner-${strat.id}`}>
            <Trophy size={13} /> ROAS WINNER
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-2 mt-4">
        <span className="mono" style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--primary)" }}>
          {usd(alloc.dollars)}
        </span>
        <span className="text-sm" style={{ color: "var(--text-secondary)" }}>/ {(alloc.share * 100).toFixed(0)}% of budget</span>
      </div>

      <div className="mt-4 space-y-2">
        {Object.entries(alloc.perChannel).map(([ch, amt]) => (
          <div key={ch} className="flex justify-between text-sm">
            <span style={{ color: "var(--text-secondary)" }}>{labels[ch] || ch}</span>
            <span className="mono">{usd(amt)}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 mt-5 pt-5 border-t" style={{ borderColor: "var(--border)" }}>
        <div><Overline>Revenue</Overline><div className="money text-xl">{usd(metrics.revenue)}</div></div>
        <div><Overline>ROAS</Overline><div className="mono text-xl" style={{ color: "var(--success)" }}>{metrics.roas}×</div></div>
        <div><Overline>New Customers</Overline><div className="mono text-xl">{metrics.newCustomers}</div></div>
        <div><Overline>CAC</Overline><div className="mono text-xl">{metrics.cac == null ? "—" : usd(metrics.cac)}</div></div>
      </div>
    </div>
  );
}

export default function AdSmith() {
  const [data, setData] = useState(null);
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    getReports().then(setData).catch(() => {});
    getRecommendedPlan().then(setPlan).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const runWeek = async () => {
    setBusy(true);
    try {
      const res = await reconcile();
      await load();
      toast.success(`Week reconciled → budget shifted toward Strategy ${res.reallocatedTo}`, {
        description: `${usd(res.report.totalRevenue)} revenue · ${res.report.blendedRoas}× ROAS`,
      });
    } finally { setBusy(false); }
  };

  const reset = async () => { await resetLoop(); await load(); toast("Loop reset to week 1 (50/50)"); };

  if (!data) return <div className="p-10" style={{ color: "var(--text-secondary)" }}>Loading…</div>;

  const reports = data.reports;
  const latest = reports[reports.length - 1];
  const winner = latest.decision.winner;
  const chart = reports.map((r) => ({
    weekOf: r.weekOf,
    "Strategy A %": Math.round(r.allocation.strategyA.share * 100),
    "Strategy B %": Math.round(r.allocation.strategyB.share * 100),
    roas: r.blendedRoas,
  }));

  const zips = Object.entries(latest.zipBreakdown).sort((a, b) => b[1].revenue - a[1].revenue).slice(0, 5);

  return (
    <div className="p-6 md:p-12 max-w-[1200px]">
      <SectionTitle kicker="Module 02 · AdSmith"
        title="The autonomous media buyer that gets smarter every week"
        subtitle="Set a weekly budget. It splits spend across two strategies, attributes every order via promo codes, then shifts money 70/30 toward whichever produced more real revenue. Clicks are a promise. Orders are proof." />

      <div className="flex flex-wrap items-center gap-3 mb-6">
        <button className="btn btn-primary" onClick={runWeek} disabled={busy} data-testid="run-week-btn">
          <Play size={15} className="inline mr-1" /> {busy ? "Reconciling…" : "Run Next Week (watch it learn)"}
        </button>
        <button className="btn btn-ghost" onClick={reset} data-testid="reset-loop-btn">
          <RotateCcw size={15} className="inline mr-1" /> Reset to Week 1
        </button>
        <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {reports.length} weeks learned · now favoring <b>Strategy {winner}</b>
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StrategyCard strat={data.strategies.A} alloc={latest.allocation.strategyA}
          metrics={latest.metrics.strategyA} labels={data.channelLabels} isWinner={winner === "A"} />
        <StrategyCard strat={data.strategies.B} alloc={latest.allocation.strategyB}
          metrics={latest.metrics.strategyB} labels={data.channelLabels} isWinner={winner === "B"} />
      </div>

      {/* Connection-aware recommended plan */}
      {plan && (
        <div className="card p-6 md:p-8 mt-8" data-testid="recommended-plan">
          <div className="flex items-center gap-2"><Plug size={18} color="var(--primary)" /><Overline>This Week's Recommended Plan · gated by your connected platforms</Overline></div>
          <h3 className="serif text-2xl mt-1">It only spends where you're actually present</h3>
          {plan.warning && (
            <div className="mt-3 p-3 rounded-lg text-sm" style={{ background: "#fdece9", color: "#C0392B" }}>{plan.warning}</div>
          )}
          {plan.diversificationTip && (
            <div className="mt-3 p-3 rounded-lg text-sm" style={{ background: "var(--surface-alt)", color: "var(--text-secondary)" }} data-testid="diversification-tip">
              💡 {plan.diversificationTip}
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {[plan.strategyA, plan.strategyB].map((s, i) => (
              <div key={i} className="p-4 rounded-lg" style={{ border: "1px solid var(--border)" }} data-testid={`plan-strategy-${i === 0 ? "A" : "B"}`}>
                <div className="flex justify-between items-baseline">
                  <span className="font-bold">{s.displayName}</span>
                  <span className="mono" style={{ color: "var(--primary)", fontWeight: 700 }}>{usd(s.dollars)}</span>
                </div>
                <div className="mt-3 space-y-1.5">
                  {Object.entries(s.perChannel).map(([ch, amt]) => (
                    <div key={ch} className="flex justify-between text-sm">
                      <span style={{ color: "var(--text-secondary)" }}>{data.channelLabels[ch] || ch}</span>
                      <span className="mono">{usd(amt)}</span>
                    </div>
                  ))}
                  {Object.keys(s.perChannel).length === 0 && (
                    <div className="text-sm" style={{ color: "var(--text-secondary)" }}>No connected channels.</div>
                  )}
                  {s.excludedChannels.map((c) => (
                    <div key={c.channel} className="flex justify-between text-sm" style={{ opacity: 0.5 }} data-testid={`excluded-${c.platform}`}>
                      <span style={{ textDecoration: "line-through" }}>{c.label}</span>
                      <span className="text-xs">not connected</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs mt-3" style={{ color: "var(--text-secondary)" }}>
            Toggle platforms in <b>Connections</b> — struck-through channels are ones AdSmith won't recommend until you connect them.
          </p>
        </div>
      )}

      {/* Learning chart */}
      <div className="card p-6 md:p-8 mt-8">
        <Overline style={{ color: "var(--primary)" }}>The Learning Loop</Overline>
        <h3 className="serif text-2xl mt-1">50/50 → 70/30 → 80/20 — money follows the winner</h3>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={chart} margin={{ top: 12, right: 12, left: -8, bottom: 0 }}>
            <defs>
              <linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#D35400" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#D35400" stopOpacity={0.03} />
              </linearGradient>
              <linearGradient id="gb" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2980B9" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#2980B9" stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E8E6DF" vertical={false} />
            <XAxis dataKey="weekOf" tick={{ fontSize: 11, fill: "#5C5A56" }} tickLine={false} axisLine={{ stroke: "#E8E6DF" }} />
            <YAxis tick={{ fontSize: 11, fill: "#5C5A56" }} tickLine={false} axisLine={false} unit="%" />
            <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #E8E6DF", fontFamily: "JetBrains Mono" }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area type="monotone" dataKey="Strategy A %" stroke="#D35400" strokeWidth={2} fill="url(#ga)" />
            <Area type="monotone" dataKey="Strategy B %" stroke="#2980B9" strokeWidth={2} fill="url(#gb)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Zip breakdown */}
      <div className="card p-6 md:p-8 mt-8">
        <div className="flex items-center gap-2"><MapPin size={18} color="var(--primary)" /><Overline>Where the money came from</Overline></div>
        <h3 className="serif text-2xl mt-1">Revenue by ZIP · this week</h3>
        <div className="mt-4 space-y-2">
          {zips.map(([zip, s]) => {
            const max = Math.max(...zips.map((z) => z[1].revenue));
            return (
              <div key={zip} className="flex items-center gap-3" data-testid={`zip-${zip}`}>
                <span className="mono text-sm" style={{ minWidth: 60 }}>{zip}</span>
                <div className="flex-1 h-6 rounded" style={{ background: "var(--surface-alt)" }}>
                  <motion.div initial={{ width: 0 }} animate={{ width: `${(s.revenue / max) * 100}%` }}
                    className="h-6 rounded" style={{ background: "var(--success)" }} />
                </div>
                <span className="money text-sm" style={{ minWidth: 90, textAlign: "right" }}>{usd(s.revenue)}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
