"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import {
  CalendarDays,
  Mic,
  Search,
  Brain,
  Settings,
  LogOut,
  Smartphone,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/meetings", icon: CalendarDays, label: "Meetings" },
  { href: "/memos", icon: Mic, label: "Voice Memos" },
  { href: "/search", icon: Search, label: "Search" },
  { href: "/memory", icon: Brain, label: "Memory" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex flex-col w-16 lg:w-56 bg-zinc-950 border-r border-zinc-900 h-screen sticky top-0 flex-shrink-0">
      {/* Logo */}
      <div className="p-4 border-b border-zinc-900">
        <Link href="/meetings" className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-lime-500 flex items-center justify-center flex-shrink-0">
            <span className="text-black font-black text-sm">L</span>
          </div>
          <span className="text-white font-semibold text-sm hidden lg:block tracking-wide">
            LIME
          </span>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-2 space-y-1">
        {navItems.map(({ href, icon: Icon, label }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors",
                active
                  ? "bg-lime-500/10 text-lime-400"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900"
              )}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm hidden lg:block">{label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom actions */}
      <div className="p-2 border-t border-zinc-900 space-y-1">
        <Link
          href="/capture"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-zinc-500 hover:text-lime-400 hover:bg-lime-500/10 transition-colors"
          title="Mobile capture"
        >
          <Smartphone className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm hidden lg:block">Capture</span>
        </Link>
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900 transition-colors"
        >
          <LogOut className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm hidden lg:block">Sign out</span>
        </button>
      </div>
    </aside>
  );
}
