"use client";

import { useCallback, useState } from "react";
import { search } from "@/lib/api";
import type { SearchResult } from "@/lib/types";
import { formatDuration } from "@/lib/utils";
import Link from "next/link";
import { Search, Loader, ArrowRight } from "lucide-react";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(
    async (q: string) => {
      if (!q.trim()) return;
      setLoading(true);
      setError(null);
      try {
        const r = await search(q);
        setResults(r);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Search failed");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runSearch(query);
  };

  const hasResults =
    results &&
    (results.segments.length > 0 || results.summaries.length > 0);

  return (
    <div className="min-h-screen">
      <div className="sticky top-0 z-10 bg-zinc-950/95 backdrop-blur border-b border-zinc-900 px-6 py-4">
        <form onSubmit={handleSubmit} className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="What did Marco say about the budget?"
              className="w-full bg-zinc-900 border border-zinc-800 rounded-xl pl-10 pr-4 py-3 text-white placeholder-zinc-600 focus:border-zinc-600 outline-none text-sm"
              autoFocus
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-4 py-3 bg-lime-500 hover:bg-lime-400 disabled:bg-zinc-800 disabled:text-zinc-600 text-black font-medium rounded-xl transition-colors"
          >
            {loading ? (
              <Loader className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowRight className="w-4 h-4" />
            )}
          </button>
        </form>
      </div>

      <div className="px-6 py-6">
        {error && (
          <div className="text-red-400 text-sm bg-red-950/30 rounded-lg p-4 mb-4">
            {error}
          </div>
        )}

        {!results && !loading && (
          <div className="text-center py-16 text-zinc-600">
            <Search className="w-10 h-10 mx-auto mb-4 text-zinc-800" />
            <p className="text-sm">Ask anything about your meetings</p>
            <p className="text-xs mt-1 text-zinc-700">
              Natural language · Searches all recordings, transcripts, and summaries
            </p>
          </div>
        )}

        {results && !loading && !hasResults && (
          <div className="text-center py-16 text-zinc-500">
            <p className="text-sm">No results for &ldquo;{results.query}&rdquo;</p>
          </div>
        )}

        {hasResults && (
          <div className="space-y-6">
            {/* Meeting summaries */}
            {results.summaries.length > 0 && (
              <section>
                <h2 className="text-zinc-400 text-xs font-medium uppercase tracking-wider mb-3">
                  Meeting summaries
                </h2>
                <div className="space-y-2">
                  {results.summaries.map((s, i) => (
                    <Link
                      key={i}
                      href={`/meetings/${s.meeting_id}`}
                      className="block p-4 bg-zinc-900 rounded-xl border border-zinc-800 hover:border-zinc-700 transition-colors"
                    >
                      <p className="text-zinc-300 text-sm line-clamp-3">{s.summary}</p>
                      <p className="text-zinc-600 text-xs mt-2">
                        Relevance: {Math.round((1 - s.distance) * 100)}%
                      </p>
                    </Link>
                  ))}
                </div>
              </section>
            )}

            {/* Transcript segments */}
            {results.segments.length > 0 && (
              <section>
                <h2 className="text-zinc-400 text-xs font-medium uppercase tracking-wider mb-3">
                  Transcript matches
                </h2>
                <div className="space-y-2">
                  {results.segments.map((seg, i) => (
                    <Link
                      key={i}
                      href={`/meetings/${seg.meeting_id}#t=${seg.start_time}`}
                      className="block p-4 bg-zinc-900 rounded-xl border border-zinc-800 hover:border-zinc-700 transition-colors"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        {seg.speaker && (
                          <span className="text-zinc-500 text-xs">{seg.speaker}</span>
                        )}
                        <span className="text-zinc-600 text-xs font-mono">
                          {formatDuration(seg.start_time)}
                        </span>
                      </div>
                      <p className="text-zinc-300 text-sm">{seg.text}</p>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
