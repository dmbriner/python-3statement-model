"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Route } from "next";
import clsx from "clsx";

const links = [
  { href: "/" as Route, label: "Dashboard" },
  { href: "/model" as Route, label: "Model" },
  { href: "/market" as Route, label: "Market" },
  { href: "/analyses" as Route, label: "Saved Analyses" },
  { href: "/profiles" as Route, label: "API Profiles" },
] as const;

export function AppNav() {
  const pathname = usePathname();

  return (
    <div className="panel soft" style={{ marginTop: 18 }}>
      <div className="buttonRow">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={clsx("button secondary", pathname === link.href && "button")}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
