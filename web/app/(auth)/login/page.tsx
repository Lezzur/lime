"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, LogIn } from "lucide-react";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await signIn("credentials", {
        password,
        totp,
        redirect: false,
      });

      if (result?.error) {
        setError("Invalid password or 2FA code");
      } else {
        router.push("/meetings");
        router.refresh();
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-sm">
      <div className="text-center mb-8">
        <div className="w-12 h-12 rounded-2xl bg-lime-500 flex items-center justify-center mx-auto mb-4">
          <span className="text-black font-black text-xl">L</span>
        </div>
        <h1 className="text-white text-2xl font-semibold">LIME</h1>
        <p className="text-zinc-500 text-sm mt-1">Your meeting intelligence</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-zinc-400 text-sm mb-2">Password</label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-white placeholder-zinc-600 focus:border-zinc-600 outline-none pr-12"
              placeholder="Enter password"
              required
              autoFocus
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-zinc-400 text-sm mb-2">
            2FA Code{" "}
            <span className="text-zinc-600 font-normal">(optional)</span>
          </label>
          <input
            type="text"
            value={totp}
            onChange={(e) => setTotp(e.target.value.replace(/\D/g, "").slice(0, 6))}
            className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-white placeholder-zinc-600 focus:border-zinc-600 outline-none font-mono tracking-widest"
            placeholder="000000"
            inputMode="numeric"
            maxLength={6}
          />
        </div>

        {error && (
          <div className="bg-red-950/50 border border-red-900/50 rounded-lg px-4 py-3 text-red-400 text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !password}
          className="w-full flex items-center justify-center gap-2 bg-lime-500 hover:bg-lime-400 disabled:bg-zinc-800 disabled:text-zinc-600 text-black font-medium rounded-xl py-3 transition-colors"
        >
          {loading ? (
            <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
          ) : (
            <LogIn className="w-4 h-4" />
          )}
          Sign in
        </button>
      </form>

      <p className="text-center text-zinc-700 text-xs mt-6">
        Personal access only
      </p>
    </div>
  );
}
