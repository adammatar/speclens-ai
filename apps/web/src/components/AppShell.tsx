import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useLocale } from "../lib/i18n";

export function AppShell() {
  const { signOut } = useAuth();
  const { t, toggleLocale } = useLocale();
  const [menuOpen, setMenuOpen] = useState(false);

  const links = [
    { to: "/", label: t("nav.home"), end: true },
    { to: "/documents", label: t("nav.documents") },
    { to: "/requirements", label: t("nav.requirements") },
    { to: "/compare", label: t("nav.compare") },
    { to: "/evaluation", label: t("nav.evaluation") },
    { to: "/settings", label: t("nav.settings") },
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand-mark" onClick={() => setMenuOpen(false)}>
          Spec<span>Lens</span> AI
        </NavLink>
        <button
          type="button"
          className="nav-menu-btn"
          aria-expanded={menuOpen}
          aria-controls="primary-nav"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {t("nav.menu")}
        </button>
        <nav id="primary-nav" className={`top-nav${menuOpen ? " open" : ""}`}>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => (isActive ? "active" : undefined)}
              onClick={() => setMenuOpen(false)}
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
