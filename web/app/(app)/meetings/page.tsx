import { MeetingList } from "@/components/meetings/MeetingList";
import { Search } from "lucide-react";
import Link from "next/link";

export default function MeetingsPage() {
  return (
    <div className="min-h-screen">
      <div className="sticky top-0 z-10 bg-zinc-950/95 backdrop-blur border-b border-zinc-900 px-6 py-4 flex items-center gap-4">
        <h1 className="text-white font-semibold flex-1">Meetings</h1>
        <Link
          href="/search"
          className="flex items-center gap-2 text-zinc-500 hover:text-zinc-300 text-sm transition-colors"
        >
          <Search className="w-4 h-4" />
          <span className="hidden sm:inline">Search</span>
        </Link>
      </div>
      <MeetingList />
    </div>
  );
}
