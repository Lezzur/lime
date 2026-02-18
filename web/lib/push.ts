// In-memory store for this session (in production, persist to a database/file)
export const pushSubscriptions = new Map<string, object>();

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
    Array.from(pushSubscriptions.values()).map((sub) =>
      webpush.default.sendNotification(
        sub as Parameters<typeof webpush.default.sendNotification>[0],
        JSON.stringify(payload)
      )
    )
  );

  return results;
}
