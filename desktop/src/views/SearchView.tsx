import { useState, useRef } from "react";
import { Search, Loader2, FileText, Clock } from "lucide-react";
import { api } from "../lib/api";

interface SearchResult {
  id: string;
  meeting_id: string;
  meeting_title?: string;
  type: "segment" | "summary";
  text: string;
  score: number;
  timestamp?: number;
}

function formatTime(s?: number) {
  if (s === undefined) return "";
  const m = Math.floor(s / 60).toString().padStart(2, "0");
  const sec = Math.floor(s % 60).toString().padStart(2, "0");
  return `${m}:${sec}`;
}

export default function SearchView() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  async function runSearch(q: string) {
    if (!q.trim()) {
      setResults([]);
      setHasSearched(false);
      return;
    }
    setLoading(true);
    setHasSearched(true);
    try {
      const data = await api.search(q);
      setResults((data.results as SearchResult[]) ?? []);
    } catch (err) {
      console.error("Search failed:", err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLInputElement>) {
    const q = e.target.value;
    setQuery(q);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSearch(q), 400);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      clearTimeout(debounceRef.current);
      runSearch(query);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search input */}
      <div className="px-4 pt-4 pb-3 border-b border-[var(--lime-border)]">
        <div className="relative">
          <Search
            size={15}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--lime-text-muted)]"
          />
          {loading && (
            <Loader2
              size={13}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--lime-text-dim)] animate-spin"
            />
          )}
          <input
            ref={inputRef}
            autoFocus
            type="text"
            placeholder="Search your meetings…"
            value={query}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            className="w-full bg-[var(--lime-surface-2)] border border-[var(--lime-border)] focus:border-[var(--accent)] rounded-lg pl-10 pr-10 py-2.5 text-sm text-[var(--lime-text)] placeholder:text-[var(--lime-text-dim)] outline-none transition-colors selectable"
          />
        </div>
        <p className="text-[10px] text-[var(--lime-text-dim)] mt-1.5">
          Semantic search across transcripts, summaries, and action items
        </p>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {!hasSearched && (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-center">
            <Search size={28} className="text-[var(--lime-text-dim)]" />
            <p className="text-sm text-[var(--lime-text-muted)]">
              Search your meeting history
            </p>
            <p className="text-xs text-[var(--lime-text-dim)] max-w-[240px]">
              Try "action items from last week" or "decisions about the product roadmap"
            </p>
          </div>
        )}

        {hasSearched && !loading && results.length === 0 && (
          <p className="text-sm text-[var(--lime-text-muted)] py-8 text-center">
            No results for "{query}"
          </p>
        )}

        <div className="space-y-2">
          {results.map((result) => (
            <div
              key={result.id}
              className="p-3 rounded-lg bg-[var(--lime-surface-2)] border border-[var(--lime-border)] hover:border-[#404040] transition-colors"
            >
              <div className="flex items-center gap-2 mb-1.5">
                <FileText size={11} className="text-[var(--lime-text-dim)]" />
                <span className="text-[10px] text-[var(--lime-text-muted)] font-medium">
                  {result.meeting_title ?? result.meeting_id}
                </span>
                {result.timestamp !== undefined && (
                  <span className="flex items-center gap-1 text-[10px] text-[var(--lime-text-dim)]">
                    <Clock size={9} />
                    {formatTime(result.timestamp)}
                  </span>
                )}
                <span
                  className="ml-auto text-[10px] px-1.5 py-0.5 rounded text-[var(--lime-text-dim)] bg-white/5"
                >
                  {result.type}
                </span>
              </div>
              <p className="text-xs text-[var(--lime-text)] leading-relaxed selectable">
                {result.text}
              </p>
              {result.score !== undefined && (
                <p className="text-[10px] text-[var(--lime-text-dim)] mt-1">
                  Relevance: {Math.round(result.score * 100)}%
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
