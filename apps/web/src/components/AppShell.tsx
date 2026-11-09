import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useLocale } from "../lib/i18n";

export function AppShell() {
  const { signOut } = useAuth();
  const { t, toggleLocale } = useLocale();

  const links = [
    { to: "/", label: t("nav.home"), end: true },
    { to: "/documents", label: t("nav.documents") },
    { to: "/settings", label: t("nav.settings") },
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand-mark">
          Spec<span>Lens</span> AI
        </NavLink>
        <nav className="top-nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => (isActive ? "active" : undefined)}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="row">
          <button
            type="button"
            className="lang-toggle"
            onClick={toggleLocale}
            title={t("lang.toggleTitle")}
          >
            {t("lang.toggle")}
          </button>
          <button type="button" className="btn secondary sm" onClick={signOut}>
            {t("nav.signOut")}
          </button>
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
