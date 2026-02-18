"use client";

import { useEffect } from "react";

export function ServiceWorkerRegistrar() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/sw.js", { scope: "/" })
        .then((reg) => {
          reg.update();

          // Listen for messages from SW (e.g., process offline queue)
          navigator.serviceWorker.addEventListener("message", (event) => {
            if (event.data?.type === "PROCESS_OFFLINE_QUEUE") {
              window.dispatchEvent(new CustomEvent("lime:process-queue"));
            }
          });
        })
        .catch((err) => console.error("SW registration failed:", err));
    }
  }, []);

  return null;
}
