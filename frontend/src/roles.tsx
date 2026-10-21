// Role switcher state (no real login). Remembered in localStorage.
import { createContext, useContext, useState, type ReactNode } from "react";

export type Role = "employee" | "reviewer" | "admin";

export const USERS: Record<Role, { name: string; title: string; home: string }> = {
  employee: { name: "Rachel Lim", title: "Branch Service Officer", home: "/chat" },
  reviewer: { name: "Daniel Ng", title: "Payments Operations", home: "/review" },
  admin: { name: "Priya Nair", title: "AI Platform team", home: "/admin" },
};

const RoleContext = createContext<{ role: Role; setRole: (r: Role) => void }>({
  role: "employee",
  setRole: () => {},
});

function initialRole(): Role {
  try {
    const saved = localStorage.getItem("qai-role");
    if (saved === "employee" || saved === "reviewer" || saved === "admin") return saved;
  } catch {
    /* storage blocked */
  }
  return "employee";
}

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>(initialRole);
  const setRole = (r: Role) => {
    setRoleState(r);
    try {
      localStorage.setItem("qai-role", r);
    } catch {
      /* storage blocked */
    }
  };
  return <RoleContext.Provider value={{ role, setRole }}>{children}</RoleContext.Provider>;
}

export const useRole = () => useContext(RoleContext);
