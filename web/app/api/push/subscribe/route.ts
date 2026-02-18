import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";

// In-memory store for this session (in production, persist to a database/file)
const subscriptions = new Map<string, object>();

export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const subscription = await req.json();
  if (!subscription?.endpoint) {
    return NextResponse.json({ error: "Invalid subscription" }, { status: 400 });
  }

  subscriptions.set(subscription.endpoint, subscription);
  return NextResponse.json({ status: "subscribed" });
}

export async function DELETE(req: NextRequest) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { endpoint } = await req.json();
  subscriptions.delete(endpoint);
  return NextResponse.json({ status: "unsubscribed" });
}

// Exported for the backend to call (send push to all subscribers)
export async function sendPushToAll(
  payload: { title: string; body: string; meeting_id?: string; tag?: string }
) {
  const webpush = await import("web-push");

  const vapidPublicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
  const vapidPrivateKey = process.env.VAPID_PRIVATE_KEY;
  const vapidMailto = process.env.VAPID_MAILTO ?? "mailto:admin@localhost";

  if (!vapidPublicKey || !vapidPrivateKey) return;

  webpush.default.setVapidDetails(vapidMailto, vapidPublicKey, vapidPrivateKey);

  const results = await Promise.allSettled(
    Array.from(subscriptions.values()).map((sub) =>
      webpush.default.sendNotification(
        sub as Parameters<typeof webpush.default.sendNotification>[0],
        JSON.stringify(payload)
      )
    )
  );

  return results;
}
