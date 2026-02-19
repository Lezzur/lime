import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import bcrypt from "bcryptjs";
import { authenticator } from "otplib";
import { authConfig } from "./auth.config";

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  providers: [
    Credentials({
      credentials: {
        password: { label: "Password", type: "password" },
        totp: { label: "2FA Code", type: "text" },
      },
      authorize: async (credentials) => {
        const passwordHash = process.env.LIME_PASSWORD_HASH;
        if (!passwordHash) {
          throw new Error("Server not configured: LIME_PASSWORD_HASH missing");
        }

        const password = credentials?.password as string;
        if (!password) return null;

        const valid = await bcrypt.compare(password, passwordHash);
        if (!valid) return null;

        const twoFaEnabled = process.env.LIME_2FA_ENABLED === "true";
        if (twoFaEnabled) {
          const secret = process.env.LIME_2FA_SECRET;
          if (!secret) throw new Error("2FA enabled but LIME_2FA_SECRET not set");
          const totp = credentials?.totp as string;
          if (!totp) return null;
          const totpValid = authenticator.check(totp, secret);
          if (!totpValid) return null;
        }

        return { id: "lime-user", name: "LIME", email: "lime@local" };
      },
    }),
  ],
});
