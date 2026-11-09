import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/documents", label: "Documents" },
  { to: "/settings", label: "Settings" },
];

export function AppShell() {
  const { signOut } = useAuth();
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand-mark">
          Spec<span>Lens</span>
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
        <button type="button" className="btn secondary sm" onClick={signOut}>
          Sign out
        </button>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
