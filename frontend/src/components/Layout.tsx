// Page shell: top bar (logo, nav, role switcher), content, footer.
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import Logo from "./Logo";
import { USERS, useRole, type Role } from "../roles";

const NAV: Record<Role, { to: string; label: string }[]> = {
  employee: [
    { to: "/chat", label: "Ask OCBC AI" },
    { to: "/trust", label: "Trust Challenge" },
  ],
  reviewer: [
    { to: "/review", label: "Review queue" },
    { to: "/kb", label: "Knowledge base" },
  ],
  admin: [
    { to: "/admin", label: "Dashboard" },
    { to: "/kb", label: "Knowledge base" },
    { to: "/trust", label: "Trust Challenge" },
    { to: "/settings", label: "Settings" },
  ],
};

export default function Layout() {
  const { role, setRole } = useRole();
  const navigate = useNavigate();

  const switchRole = (r: Role) => {
    setRole(r);
    navigate(USERS[r].home);
  };

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
          <Logo />
          <nav className="order-3 flex w-full gap-1 overflow-x-auto sm:order-none sm:w-auto" aria-label="Main">
            {NAV[role].map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium ${
                    isActive ? "bg-brand-tint text-brand-dark" : "text-ink-muted hover:text-ink"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <label htmlFor="role" className="hidden text-xs font-medium text-ink-muted md:block">
              Viewing as
            </label>
            <select
              id="role"
              value={role}
              onChange={(e) => switchRole(e.target.value as Role)}
              className="rounded-xl border border-line bg-surface px-2 py-1.5 text-sm font-medium text-ink"
            >
              {(Object.keys(USERS) as Role[]).map((r) => (
                <option key={r} value={r}>
                  {USERS[r].name} · {USERS[r].title}
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
        <Outlet />
      </main>

      <footer className="border-t border-line bg-surface">
        <p className="mx-auto max-w-7xl px-4 py-4 text-center text-xs text-ink-muted sm:px-6">
          Prototype for OCBC Ignite. Synthetic data only. Not an OCBC product.
        </p>
      </footer>
    </div>
  );
}
