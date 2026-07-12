import { NavLink } from "react-router-dom";
import { LayoutDashboard, Clapperboard, TrendingUp, QrCode, Utensils } from "lucide-react";

const items = [
  { to: "/", label: "Overview", icon: LayoutDashboard, testid: "nav-overview", end: true },
  { to: "/content", label: "Content Director", icon: Clapperboard, testid: "nav-content" },
  { to: "/adsmith", label: "AdSmith", icon: TrendingUp, testid: "nav-adsmith" },
  { to: "/echolink", label: "EchoLink", icon: QrCode, testid: "nav-echolink" },
];

export default function Sidebar() {
  return (
    <aside
      className="hidden md:flex md:flex-col md:w-64 shrink-0 border-r px-5 py-8"
      style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      data-testid="sidebar"
    >
      <div className="flex items-center gap-2 mb-1">
        <div
          className="grid place-items-center rounded-lg"
          style={{ width: 38, height: 38, background: "var(--primary)" }}
        >
          <Utensils size={20} color="#fff" />
        </div>
        <div>
          <div className="serif text-2xl leading-none" style={{ fontWeight: 600 }}>
            Expo Proxy
          </div>
          <div className="overline" style={{ fontSize: "0.55rem" }}>
            Revenue Engine
          </div>
        </div>
      </div>

      <nav className="mt-10 flex flex-col gap-1">
        {items.map(({ to, label, icon: Icon, testid, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            data-testid={testid}
            className="nav-item flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-semibold"
            style={({ isActive }) => ({
              background: isActive ? "var(--surface-alt)" : "transparent",
              color: isActive ? "var(--primary)" : "var(--text-secondary)",
              borderLeft: isActive ? "3px solid var(--primary)" : "3px solid transparent",
            })}
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div
        className="mt-auto text-xs p-4 rounded-lg"
        style={{ background: "var(--surface-alt)", color: "var(--text-secondary)" }}
      >
        <div className="serif text-lg" style={{ color: "var(--text)" }}>$299/mo</div>
        Cancel your $750 Valpak. This targets, converts &amp; proves it — and learns every week.
      </div>
    </aside>
  );
}
