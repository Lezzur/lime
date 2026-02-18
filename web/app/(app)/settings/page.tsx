"use client";

import { useState } from "react";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import { Bell, BellOff, Settings2, Smartphone, Lock } from "lucide-react";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const [wakeWord, setWakeWord] = useState("koda");
  const [confidenceThreshold, setConfidenceThreshold] = useState(70);
  const { permission, subscription, subscribe, unsubscribe } = usePushNotifications();

  return (
    <div className="min-h-screen">
      <div className="border-b border-zinc-900 px-6 py-4 flex items-center gap-3">
        <Settings2 className="w-5 h-5 text-zinc-400" />
        <h1 className="text-white font-semibold">Settings</h1>
      </div>

      <div className="px-6 py-6 max-w-xl space-y-8">
        {/* Notifications */}
        <section>
          <h2 className="text-zinc-300 font-medium mb-4 flex items-center gap-2">
            <Bell className="w-4 h-4" />
            Push Notifications
          </h2>
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white text-sm">Meeting processed alerts</p>
                <p className="text-zinc-500 text-xs mt-0.5">
                  Notify when LIME finishes analyzing a meeting
                </p>
              </div>
              {permission === "granted" && subscription ? (
                <button
                  onClick={unsubscribe}
                  className="flex items-center gap-2 px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs rounded-lg transition-colors"
                >
                  <BellOff className="w-3.5 h-3.5" />
                  Disable
                </button>
              ) : (
                <button
                  onClick={subscribe}
                  className="flex items-center gap-2 px-3 py-2 bg-lime-500 hover:bg-lime-400 text-black text-xs font-medium rounded-lg transition-colors"
                >
                  <Bell className="w-3.5 h-3.5" />
                  Enable
                </button>
              )}
            </div>
            {permission === "denied" && (
              <p className="text-amber-400 text-xs mt-3">
                Notifications blocked by browser. Update permissions in browser settings.
              </p>
            )}
          </div>
        </section>

        {/* Wake word */}
        <section>
          <h2 className="text-zinc-300 font-medium mb-4 flex items-center gap-2">
            <Smartphone className="w-4 h-4" />
            Capture Settings
          </h2>
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 divide-y divide-zinc-800">
            <div className="p-4">
              <label className="block text-white text-sm mb-2">Wake word</label>
              <p className="text-zinc-500 text-xs mb-3">
                Say &ldquo;Hey [word], go discreet&rdquo; or &ldquo;Hey [word], active mode&rdquo; during capture
              </p>
              <input
                type="text"
                value={wakeWord}
                onChange={(e) => setWakeWord(e.target.value.toLowerCase())}
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:border-zinc-500 outline-none w-40"
                placeholder="koda"
              />
            </div>
            <div className="p-4">
              <label className="block text-white text-sm mb-1">Confidence badge threshold</label>
              <p className="text-zinc-500 text-xs mb-3">
                Items below this confidence show a percentage badge
              </p>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-zinc-300 text-sm font-mono w-12 text-right">
                  {confidenceThreshold}%
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Security */}
        <section>
          <h2 className="text-zinc-300 font-medium mb-4 flex items-center gap-2">
            <Lock className="w-4 h-4" />
            Security
          </h2>
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white text-sm">Two-factor authentication</p>
                <p className="text-zinc-500 text-xs mt-0.5">TOTP via authenticator app</p>
              </div>
              <span
                className={cn(
                  "text-xs px-2 py-1 rounded",
                  process.env.NEXT_PUBLIC_2FA_ENABLED === "true"
                    ? "bg-green-900/50 text-green-400"
                    : "bg-zinc-800 text-zinc-500"
                )}
              >
                {process.env.NEXT_PUBLIC_2FA_ENABLED === "true" ? "Enabled" : "Disabled"}
              </span>
            </div>
            <p className="text-zinc-600 text-xs">
              Configure 2FA via <code className="text-zinc-500">LIME_2FA_ENABLED</code> and{" "}
              <code className="text-zinc-500">LIME_2FA_SECRET</code> in your .env file.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
