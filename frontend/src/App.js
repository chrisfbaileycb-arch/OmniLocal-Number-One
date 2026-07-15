import { useEffect, useState } from "react";
import "@/App.css";
import { Toaster } from "sonner";
import { LayoutDashboard, Clapperboard, TrendingUp, Sparkles, UtensilsCrossed } from "lucide-react";
import Overview from "@/sections/Overview";
import ContentDirector from "@/sections/ContentDirector";
import Executioner from "@/sections/Executioner";
import Maximizer from "@/sections/Maximizer";
import { getOverview } from "@/lib/api";

const NAV = [
  { id: "overview", label: "Command Center", icon: LayoutDashboard },
  { id: "executioner", label: "Quality Content Executioner", icon: TrendingUp },
  { id: "maximizer", label: "Quality Customer Maximizer", icon: Sparkles },
  { id: "content", label: "Content Director", icon: Clapperboard },
];

function App() {
  const [active, setActive] = useState("overview");
  const [brand, setBrand] = useState(null);

  useEffect(() => { getOverview().then((d) => setBrand(d.brand)).catch(() => {}); }, []);

  return (
    <div className="App" style={{ background: "var(--bone)" }}>
      <Toaster position="top-right" richColors />
      <div className="flex min-h-screen">
        {/* Sidebar */}
        <aside className="w-64 shrink-0 border-r hidden md:flex flex-col fixed h-screen"
               style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="p-6 border-b" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: "var(--primary)" }}>
                <UtensilsCrossed size={18} color="#fff" />
              </div>
              <div>
                <div className="serif text-xl leading-none" style={{ fontWeight: 600 }}>OmniLocal #1</div>
                <div className="overline" style={{ fontSize: "0.55rem" }}>Revenue Engine</div>
              </div>
            </div>
          </div>

          <nav className="p-3 flex-1">
            {NAV.map((n) => {
              const Icon = n.icon;
              const on = active === n.id;
              return (
                <button key={n.id} data-testid={`nav-${n.id}`} onClick={() => setActive(n.id)}
                  className="nav-item w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-1 text-left"
                  style={{ background: on ? "var(--surface-alt)" : "transparent",
                           color: on ? "var(--primary)" : "var(--text-secondary)", fontWeight: on ? 700 : 500 }}>
                  <Icon size={18} />
                  <span className="text-sm">{n.label}</span>
                </button>
              );
            })}
          </nav>

          {brand && (
            <div className="p-4 m-3 rounded-lg" style={{ background: "var(--surface-alt)" }}>
              <div className="overline" style={{ fontSize: "0.55rem" }}>Active Restaurant</div>
              <div className="serif text-lg" style={{ fontWeight: 600 }}>{brand.name}</div>
              <div className="text-xs" style={{ color: "var(--text-secondary)" }}>{brand.city} · {brand.signatureItem}</div>
            </div>
          )}
        </aside>

        <main className="flex-1 md:ml-64">
          {/* Mobile nav */}
          <div className="md:hidden flex gap-1 p-2 border-b overflow-x-auto sticky top-0 z-20"
               style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            {NAV.map((n) => (
              <button key={n.id} data-testid={`mnav-${n.id}`} onClick={() => setActive(n.id)}
                className="px-3 py-2 rounded-lg text-xs whitespace-nowrap"
                style={{ background: active === n.id ? "var(--surface-alt)" : "transparent",
                         color: active === n.id ? "var(--primary)" : "var(--text-secondary)", fontWeight: 600 }}>
                {n.label}
              </button>
            ))}
          </div>

          {active === "overview" && <Overview onNavigate={setActive} />}
          {active === "executioner" && <Executioner />}
          {active === "maximizer" && <Maximizer />}
          {active === "content" && <ContentDirector />}
        </main>
      </div>
    </div>
  );
}

export default App;
