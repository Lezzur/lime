"use client";

import { useCallback, useEffect, useState } from "react";
import { openDB, type IDBPDatabase } from "idb";
import type { OfflineRecording } from "@/lib/types";

const DB_NAME = "lime-offline";
const STORE = "recordings";

async function getDB(): Promise<IDBPDatabase> {
  return openDB(DB_NAME, 1, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "id" });
      }
    },
  });
}

export function useOfflineQueue() {
  const [queue, setQueue] = useState<OfflineRecording[]>([]);
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );

  const refreshQueue = useCallback(async () => {
    const db = await getDB();
    const all = await db.getAll(STORE);
    setQueue(all as OfflineRecording[]);
  }, []);

  const enqueue = useCallback(
    async (recording: Omit<OfflineRecording, "status">) => {
      const db = await getDB();
      const item: OfflineRecording = { ...recording, status: "queued" };
      await db.put(STORE, item);
      await refreshQueue();
    },
    [refreshQueue]
  );

  const processQueue = useCallback(async () => {
    if (!isOnline) return;
    const db = await getDB();
    const items = (await db.getAll(STORE)) as OfflineRecording[];
    const pending = items.filter((i) => i.status === "queued" || i.status === "failed");

    for (const item of pending) {
      try {
        await db.put(STORE, { ...item, status: "uploading" });

        const formData = new FormData();
        formData.append("audio", item.blob, "recording.webm");
        if (item.meeting_title) formData.append("title", item.meeting_title);
        formData.append("type", item.type);

        const endpoint =
          item.type === "voice_memo" ? "/api/lime/voice-memo" : "/api/lime/meetings/upload";

        const res = await fetch(endpoint, { method: "POST", body: formData });
        if (!res.ok) throw new Error(`Upload failed: ${res.status}`);

        await db.put(STORE, { ...item, status: "done" });
      } catch {
        await db.put(STORE, { ...item, status: "failed" });
      }
    }
    await refreshQueue();
  }, [isOnline, refreshQueue]);

  const clearDone = useCallback(async () => {
    const db = await getDB();
    const all = (await db.getAll(STORE)) as OfflineRecording[];
    for (const item of all) {
      if (item.status === "done") await db.delete(STORE, item.id);
    }
    await refreshQueue();
  }, [refreshQueue]);

  useEffect(() => {
    const onOnline = () => {
      setIsOnline(true);
      processQueue();
    };
    const onOffline = () => setIsOnline(false);

    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    refreshQueue();

    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, [processQueue, refreshQueue]);

  return { queue, isOnline, enqueue, processQueue, clearDone };
}
