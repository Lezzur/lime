"""
Memory consolidation engine.

Runs no more than once per day during idle time.
Minimum frequency: once every 2 weeks.
Never interrupts user activity.

Process:
  1. Read all short-term entries
  2. Group by similarity (signal_type + content fingerprint)
  3. Promote repeated signals → medium-term patterns
  4. Promote reinforced patterns → long-term confirmed rules
  5. Clean consumed short-term entries
"""

import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Optional

from backend.learning.memory import (
    MemoryStore,
    MemoryEntry,
    PatternEntry,
    ConfirmedRule,
    SignalType,
    memory,
)

logger = logging.getLogger(__name__)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class ConsolidationEngine:
    """
    Promotes signals through the three memory tiers.
    Short-term → Medium-term: when a signal appears N+ times.
    Medium-term → Long-term: when a pattern is observed N+ total times.
    """

    SIMILARITY_THRESHOLD = 0.7  # Two signals are "same" if content similarity >= this

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or memory
        self._lock = threading.Lock()
        self._last_run: Optional[datetime] = None

    def run(self) -> dict:
        """
        Execute a full consolidation pass. Returns stats.
        Thread-safe — only one consolidation runs at a time.
        """
        if not self._lock.acquire(blocking=False):
            logger.info("Consolidation already running, skipping.")
            return {"skipped": True}

        try:
            logger.info("Memory consolidation starting...")
            stats = {"promoted_to_medium": 0, "promoted_to_long": 0, "signals_consumed": 0}

            short_entries = self.store.read_short_term_entries()
            if not short_entries:
                logger.info("No short-term signals to consolidate.")
                return stats

            medium_patterns = self.store.read_medium_term_patterns()
            long_rules = self.store.read_long_term_rules()

            # Phase 1: Group short-term by similarity
            groups = self._group_signals(short_entries)

            # Phase 2: Update or create medium-term patterns
            for key, entries in groups.items():
                signal_type, _ = key
                pattern = self._find_matching_pattern(entries[0].content, signal_type, medium_patterns)

                if pattern:
                    # Reinforce existing pattern
                    pattern.observation_count += len(entries)
                    pattern.last_seen = entries[-1].timestamp
                    for e in entries:
                        pattern.supporting_evidence.append(
                            f"[{e.timestamp}] {e.content[:80]}"
                        )
                    # Trim evidence to last 10
                    pattern.supporting_evidence = pattern.supporting_evidence[-10:]
                else:
                    # Check if enough signals to promote
                    if len(entries) >= self.store.PROMOTION_TO_MEDIUM_THRESHOLD:
                        new_pattern = PatternEntry(
                            pattern=self._synthesize_pattern(entries),
                            signal_type=signal_type,
                            observation_count=len(entries),
                            first_seen=entries[0].timestamp,
                            last_seen=entries[-1].timestamp,
                            supporting_evidence=[
                                f"[{e.timestamp}] {e.content[:80]}" for e in entries[-5:]
                            ],
                        )
                        medium_patterns.append(new_pattern)
                        stats["promoted_to_medium"] += 1
                        logger.info(f"New pattern promoted to medium-term: {new_pattern.pattern[:60]}")

            # Phase 3: Promote mature patterns to long-term
            remaining_medium = []
            long_rule_texts = {r.rule.lower() for r in long_rules}

            for pattern in medium_patterns:
                if (
                    pattern.observation_count >= self.store.PROMOTION_TO_LONG_THRESHOLD
                    and pattern.pattern.lower() not in long_rule_texts
                ):
                    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                    rule = ConfirmedRule(
                        rule=pattern.pattern,
                        signal_type=pattern.signal_type,
                        promoted_from=pattern.id,
                        promoted_at=now,
                        context_scope=pattern.context_scope,
                    )
                    long_rules.append(rule)
                    stats["promoted_to_long"] += 1
                    logger.info(f"Pattern promoted to long-term: {rule.rule[:60]}")
                else:
                    remaining_medium.append(pattern)

            # Phase 4: Write updated tiers
            self.store.write_medium_term(remaining_medium)
            self.store.write_long_term(long_rules)
            self.store.clear_short_term()
            stats["signals_consumed"] = len(short_entries)

            self._last_run = datetime.now(timezone.utc)
            logger.info(
                f"Consolidation complete: "
                f"{stats['signals_consumed']} signals consumed, "
                f"{stats['promoted_to_medium']} → medium, "
                f"{stats['promoted_to_long']} → long"
            )
            return stats

        finally:
            self._lock.release()

    def _group_signals(
        self, entries: list[MemoryEntry]
    ) -> dict[tuple[str, str], list[MemoryEntry]]:
        """
        Group entries by signal_type + content similarity.
        Returns {(signal_type, group_key): [entries]}.
        """
        groups: dict[tuple[str, str], list[MemoryEntry]] = {}

        for entry in entries:
            matched = False
            for key, group in groups.items():
                if key[0] != entry.signal_type:
                    continue
                # Compare with the first entry in the group
                if _similarity(entry.content, group[0].content) >= self.SIMILARITY_THRESHOLD:
                    group.append(entry)
                    matched = True
                    break

            if not matched:
                fingerprint = entry.content[:50].lower().strip()
                groups[(entry.signal_type, fingerprint)] = [entry]

        return groups

    def _find_matching_pattern(
        self, content: str, signal_type: str, patterns: list[PatternEntry]
    ) -> Optional[PatternEntry]:
        for p in patterns:
            if p.signal_type != signal_type:
                continue
            if _similarity(content, p.pattern) >= self.SIMILARITY_THRESHOLD:
                return p
        return None

    def _synthesize_pattern(self, entries: list[MemoryEntry]) -> str:
        """
        Create a pattern description from a group of similar signals.
        Uses the most common phrasing as the representative.
        """
        if len(entries) == 1:
            return entries[0].content

        # Pick the entry with highest average similarity to all others
        best_entry = entries[0]
        best_score = 0
        for e in entries:
            score = sum(_similarity(e.content, other.content) for other in entries) / len(entries)
            if score > best_score:
                best_score = score
                best_entry = e

        count = len(entries)
        return f"{best_entry.content} (observed {count} times)"


# Module-level singleton
consolidator = ConsolidationEngine()
