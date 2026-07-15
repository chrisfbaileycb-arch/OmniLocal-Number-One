import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { TrendingUp, Users, Wallet, Repeat, Check, X } from "lucide-react";
import { getOverview } from "@/lib/api";
import { SectionTitle, Overline, usd } from "@/components/ui-bits";

function Metric({ label, value, sub, icon: Icon, accent }) {
  return (
    <div className="card lift p-6" data-testid={`metric-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="flex items-center justify-between">
        <Overline>{label}</Overline>
        {Icon && <Icon size={18} style={{ color: accent || "var(--text-secondary)" }} />}
      </div>
      <div className="mono mt-3" style={{ fontSize: "2rem", fontWeight: 700, color: accent || "var(--text)", letterSpacing: "-0.03em" }}>
        {value}
      </div>
      {sub && <div className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>{sub}</div>}
    </div>
  );
}

export default function Overview() {
  const [data, setData] = useState(null);
  useEffect(() => { getOverview().then(setData).catch(() => {}); }, []);
  if (!data) return <div className="p-10" style={{ color: "var(--text-secondary)" }}>Loading revenue…</div>;

  const { brand, hero, weekly, valpak, latestWinner } = data;

  return (
    <div className="p-6 md:p-12 max-w-[1200px]">
      <Overline style={{ color: "var(--primary)" }}>{brand.name} · {brand.city}</Overline>
      <h1 className="text-4xl md:text-6xl mt-2" style={{ fontWeight: 300 }}>
        This is your one and only <span style={{ color: "var(--primary)" }}>revenue engine</span> that you will ever need.
      </h1>
      <p className="mt-3 max-w-2xl" style={{ color: "var(--text-secondary)" }}>
        Everyone else helps you look busy. This makes you money — targeting the customers who convert,
        proving the revenue at the register, and getting smarter every single week.
      </p>

      {/* Hero money counter */}
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
        className="card mt-8 p-8 md:p-10"
        style={{ background: "var(--surface-alt)" }}
        data-testid="hero-revenue"
      >
        <Overline style={{ color: "var(--success)" }}>Total Attributed Revenue · last {hero.weeksLearning} weeks</Overline>
        <div className="money mt-2" style={{ fontSize: "clamp(3rem, 8vw, 5.5rem)", fontWeight: 700, lineHeight: 1 }}>
          {usd(hero.totalAttributedRevenue)}
        </div>
        <div className="text-sm mt-2" style={{ color: "var(--text-secondary)" }}>
          On {usd(hero.totalSpend)} of ad spend · blended {hero.blendedRoas}× ROAS · {hero.newCustomers} new customers walked in.
        </div>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
        <Metric label="Blended ROAS" value={`${hero.blendedRoas}×`} sub="Revenue per $1 spent" icon={TrendingUp} accent="var(--success)" />
        <Metric label="New Customers" value={hero.newCustomers} sub="Attributed to campaigns" icon={Users} />
        <Metric label="Weekly Budget" value={usd(299)} sub="Learning + reallocating" icon={Wallet} accent="var(--primary)" />
        <Metric label="Weeks Learning" value={hero.weeksLearning} sub={`Now favoring Strategy ${latestWinner}`} icon={Repeat} />
      </div>

      {/* Learning chart */}
      <div className="card p-6 md:p-8 mt-8">
        <SectionTitle kicker="The Flywheel, Visible" title="Revenue up, spend flat, ROAS climbing"
          subtitle="Week 1 started as a 50/50 coin-flip. Every week it learns where your money converts and shifts budget toward the winner. Fluff is flat. You go up and to the right." />
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={weekly} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E8E6DF" vertical={false} />
            <XAxis dataKey="weekOf" tick={{ fontSize: 11, fill: "#5C5A56" }} tickLine={false} axisLine={{ stroke: "#E8E6DF" }} />
            <YAxis yAxisId="l" tick={{ fontSize: 11, fill: "#5C5A56" }} tickLine={false} axisLine={false} />
            <YAxis yAxisId="r" orientation="right" tick={{ fontSize: 11, fill: "#27AE60" }} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #E8E6DF", fontFamily: "JetBrains Mono" }} />
            <Line yAxisId="l" type="monotone" dataKey="revenue" name="Revenue $" stroke="#27AE60" strokeWidth={3} dot={{ r: 3 }} />
            <Line yAxisId="r" type="monotone" dataKey="roas" name="ROAS ×" stroke="#D35400" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Valpak comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
        <div className="card p-8" style={{ background: "#faf3f1", borderColor: "#e7cfc9" }} data-testid="valpak-card">
          <Overline style={{ color: "var(--danger)" }}>The Old Way · Valpak</Overline>
          <div className="mono mt-2" style={{ fontSize: "2.5rem", fontWeight: 700, color: "var(--danger)" }}>{usd(valpak.valpakCost)}</div>
          <div className="text-sm" style={{ color: "var(--text-secondary)" }}>to blanket {valpak.valpakHomes.toLocaleString()} mailboxes</div>
          <ul className="mt-4 space-y-2 text-sm">
            <li className="flex gap-2 items-center"><X size={16} color="#C0392B" /> Zero targeting</li>
            <li className="flex gap-2 items-center"><X size={16} color="#C0392B" /> Zero proof of revenue</li>
            <li className="flex gap-2 items-center"><X size={16} color="#C0392B" /> One-shot, learns nothing</li>
          </ul>
        </div>
        <div className="card p-8" style={{ background: "#f1f8f3", borderColor: "#c9e7d5" }} data-testid="ourway-card">
          <Overline style={{ color: "var(--success)" }}>This · OmniLocal #1</Overline>
          <div className="mono mt-2" style={{ fontSize: "2.5rem", fontWeight: 700, color: "var(--success)" }}>{usd(valpak.ourCost)}</div>
          <div className="text-sm" style={{ color: "var(--text-secondary)" }}>{valpak.ourReachNote}</div>
          <ul className="mt-4 space-y-2 text-sm">
            <li className="flex gap-2 items-center"><Check size={16} color="#27AE60" /> Targets converting ZIPs &amp; demographics</li>
            <li className="flex gap-2 items-center"><Check size={16} color="#27AE60" /> Tracks every ad to real orders</li>
            <li className="flex gap-2 items-center"><Check size={16} color="#27AE60" /> Learns &amp; improves every week</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
