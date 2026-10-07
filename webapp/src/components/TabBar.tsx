import { haptic } from "../tg";

export type Tab = "list" | "stats";

const TABS: { id: Tab; label: string; icon: string }[] = [
  {
    id: "list",
    label: "Список",
    icon: "M4 7h16M4 12h16M4 17h10",
  },
  {
    id: "stats",
    label: "Статистика",
    icon: "M4 19V5M10 19V9M16 19V13M22 19H2",
  },
];

export function TabBar({
  active,
  onChange,
}: {
  active: Tab;
  onChange: (tab: Tab) => void;
}) {
  return (
    <nav className="tabbar">
      {TABS.map((t) => (
        <button
          key={t.id}
          className={`tab ${active === t.id ? "active" : ""}`}
          onClick={() => {
            if (t.id !== active) haptic.select();
            onChange(t.id);
          }}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d={t.icon} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <span>{t.label}</span>
        </button>
      ))}
    </nav>
  );
}
