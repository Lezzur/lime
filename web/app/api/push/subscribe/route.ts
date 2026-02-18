import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { pushSubscriptions } from "@/lib/push";

export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const subscription = await req.json();
  if (!subscription?.endpoint) {
    return NextResponse.json({ error: "Invalid subscription" }, { status: 400 });
  }

  pushSubscriptions.set(subscription.endpoint, subscription);
  return NextResponse.json({ status: "subscribed" });
}

export async function DELETE(req: NextRequest) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { endpoint } = await req.json();
  pushSubscriptions.delete(endpoint);
  return NextResponse.json({ status: "unsubscribed" });
}
