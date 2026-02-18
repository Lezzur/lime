"use client";

import { VoiceMemoRecorder } from "@/components/voice-memo/VoiceMemoRecorder";
import { Mic } from "lucide-react";

export default function MemosPage() {
  return (
    <div className="min-h-screen">
      <div className="border-b border-zinc-900 px-6 py-4">
        <h1 className="text-white font-semibold">Voice Memos</h1>
        <p className="text-zinc-500 text-sm mt-1">
          Quick capture · 15s silence auto-end · syncs automatically
        </p>
      </div>

      <div className="px-6 py-8">
        {/* Recorder */}
        <div className="max-w-sm mx-auto bg-zinc-900 rounded-2xl border border-zinc-800">
          <div className="flex items-center gap-3 px-5 py-4 border-b border-zinc-800">
            <Mic className="w-4 h-4 text-lime-400" />
            <span className="text-white text-sm font-medium">Record memo</span>
          </div>
          <VoiceMemoRecorder
            onRecorded={(blob, duration) => {
              console.log(`Memo recorded: ${duration}s, ${blob.size} bytes`);
            }}
          />
        </div>

        <p className="text-center text-zinc-700 text-xs mt-6">
          Memos are transcribed and structured by LIME after recording
        </p>
      </div>
    </div>
  );
}
