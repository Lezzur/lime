"""
Three-tier self-learning memory system.

Tiers:
  - Short-term : Raw, granular signals (corrections, edits, preferences).
                 Timestamped entries consumed by consolidation.
  - Medium-term: Patterns detected from repeated short-term signals.
                 Promoted when a signal appears multiple times.
  - Long-term  : Confirmed truths — ground truth until user contradicts.
                 Promoted when medium-term patterns are continuously reinforced.

All tiers are stored as human-readable/editable Markdown files.
User edits to any memory file are treated as high-priority signals.
"""

import re
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class MemoryTier(str, Enum):
    short = "short-term"
    medium = "medium-term"
    long = "long-term"


class SignalType(str, Enum):
    transcription_correction = "transcription_correction"
    content_edit = "content_edit"
    content_deletion = "content_deletion"
    bookmark = "bookmark"
    priority_flag = "priority_flag"
    preference = "preference"
    vocabulary = "vocabulary"
    person = "person"
    project = "project"
    format_preference = "format_preference"
    behavior = "behavior"
    user_override = "user_override"


@dataclass
class MemoryEntry:
    timestamp: str
    signal_type: str
    content: str
    context: str = ""
    source_meeting_id: str = ""

    def to_markdown_line(self) -> str:
        parts = [f"- [{self.timestamp}]"]
        parts.append(f"**{self.signal_type}**:")
        parts.append(self.content)
        if self.context:
            parts.append(f"— _{self.context}_")
        if self.source_meeting_id:
            parts.append(f"(meeting: `{self.source_meeting_id[:8]}`)")
        return " ".join(parts)


@dataclass
class PatternEntry:
    pattern: str
    signal_type: str
    observation_count: int
    first_seen: str
    last_seen: str
    supporting_evidence: list[str] = field(default_factory=list)
    context_scope: str = "universal"  # "universal" | specific scope like "standup" or "client-meeting"

    @property
    def id(self) -> str:
        raw = f"{self.signal_type}:{self.pattern}:{self.context_scope}"
        return hashlib.md5(raw.encode()).hexdigest()[:10]

    def to_markdown_block(self) -> str:
        lines = [
            f"### [{self.id}] {self.pattern}",
            f"- **Type:** {self.signal_type}",
            f"- **Observed:** {self.observation_count} times",
            f"- **Scope:** {self.context_scope}",
            f"- **First seen:** {self.first_seen}",
            f"- **Last seen:** {self.last_seen}",
        ]
        if self.supporting_evidence:
            lines.append("- **Evidence:**")
            for e in self.supporting_evidence[-5:]:  # Keep last 5
                lines.append(f"  - {e}")
        lines.append("")
        return "\n".join(lines)


@dataclass
class ConfirmedRule:
    rule: str
    signal_type: str
    promoted_from: str  # pattern id
    promoted_at: str
    context_scope: str = "universal"

    def to_markdown_block(self) -> str:
        lines = [
            f"### CONFIRMED: {self.rule}",
            f"- **Type:** {self.signal_type}",
            f"- **Scope:** {self.context_scope}",
            f"- **Promoted:** {self.promoted_at}",
            f"- **Source pattern:** `{self.promoted_from}`",
            "",
        ]
        return "\n".join(lines)


class MemoryStore:
    """
    Reads, writes, and manages the three-tier markdown memory files.
    """

    PROMOTION_TO_MEDIUM_THRESHOLD = 3    # Short→medium after N occurrences
    PROMOTION_TO_LONG_THRESHOLD = 8      # Medium→long after N total observations
    MEDIUM_REINFORCEMENT_WINDOW = 5      # New signals within this count reinforce existing patterns

    def __init__(self, memory_dir: Optional[Path] = None):
        self.memory_dir = memory_dir or settings.memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._short_path = self.memory_dir / "short-term.md"
        self._medium_path = self.memory_dir / "medium-term.md"
        self._long_path = self.memory_dir / "long-term.md"
        self._ensure_files()

    def _ensure_files(self):
        for path, header in [
            (self._short_path, "# Short-Term Memory\n"),
            (self._medium_path, "# Medium-Term Memory\n"),
            (self._long_path, "# Long-Term Memory\n"),
        ]:
            if not path.exists():
                path.write_text(header, encoding="utf-8")

    # ── Short-Term: Record signals ────────────────────────────────────────────

    def record_signal(
        self,
        signal_type: SignalType,
        content: str,
        context: str = "",
        source_meeting_id: str = "",
    ) -> MemoryEntry:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        entry = MemoryEntry(
            timestamp=now,
            signal_type=signal_type.value,
            content=content,
            context=context,
            source_meeting_id=source_meeting_id,
        )
        self._append_to_file(self._short_path, entry.to_markdown_line())
        logger.info(f"Memory signal recorded: [{signal_type.value}] {content[:60]}")
        return entry

    # ── Read tiers ────────────────────────────────────────────────────────────

    def read_tier(self, tier: MemoryTier) -> str:
        path = self._path_for_tier(tier)
        return path.read_text(encoding="utf-8")

    def read_short_term_entries(self) -> list[MemoryEntry]:
        text = self._short_path.read_text(encoding="utf-8")
        entries = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("- ["):
                continue
            entry = self._parse_short_term_line(line)
            if entry:
                entries.append(entry)
        return entries

    def read_medium_term_patterns(self) -> list[PatternEntry]:
        text = self._medium_path.read_text(encoding="utf-8")
        return self._parse_patterns(text)

    def read_long_term_rules(self) -> list[ConfirmedRule]:
        text = self._long_path.read_text(encoding="utf-8")
        return self._parse_rules(text)

    # ── Write / Update tiers ──────────────────────────────────────────────────

    def update_tier(self, tier: MemoryTier, content: str):
        """Replace entire tier content. Used for user edits (high-priority signal)."""
        path = self._path_for_tier(tier)
        path.write_text(content, encoding="utf-8")
        logger.info(f"Memory tier '{tier.value}' updated by user.")
        # User edit to memory is itself a signal
        if tier == MemoryTier.long:
            self.record_signal(
                SignalType.user_override,
                f"User directly edited long-term memory file.",
            )

    def write_medium_term(self, patterns: list[PatternEntry]):
        header = "# Medium-Term Memory\n\n"
        body = "\n".join(p.to_markdown_block() for p in patterns)
        self._medium_path.write_text(header + body, encoding="utf-8")

    def write_long_term(self, rules: list[ConfirmedRule]):
        header = "# Long-Term Memory\n\n"
        body = "\n".join(r.to_markdown_block() for r in rules)
        self._long_path.write_text(header + body, encoding="utf-8")

    def clear_short_term(self):
        """Wipe short-term after consolidation consumes it."""
        self._short_path.write_text("# Short-Term Memory\n", encoding="utf-8")
        logger.info("Short-term memory cleared after consolidation.")

    # ── Convenience: common signal types ──────────────────────────────────────

    def record_transcription_correction(
        self, original: str, corrected: str, meeting_id: str = ""
    ):
        self.record_signal(
            SignalType.transcription_correction,
            f"Corrected '{original}' → '{corrected}'",
            source_meeting_id=meeting_id,
        )

    def record_content_edit(self, description: str, meeting_id: str = ""):
        self.record_signal(
            SignalType.content_edit,
            description,
            source_meeting_id=meeting_id,
        )

    def record_content_deletion(self, what_was_deleted: str, meeting_id: str = ""):
        self.record_signal(
            SignalType.content_deletion,
            f"User deleted: {what_was_deleted}",
            source_meeting_id=meeting_id,
        )

    def record_vocabulary(self, term: str, context: str = "", meeting_id: str = ""):
        self.record_signal(
            SignalType.vocabulary,
            f"Domain term: '{term}'",
            context=context,
            source_meeting_id=meeting_id,
        )

    def record_person(self, name: str, context: str = "", meeting_id: str = ""):
        self.record_signal(
            SignalType.person,
            f"Person encountered: {name}",
            context=context,
            source_meeting_id=meeting_id,
        )

    def record_preference(self, preference: str, meeting_id: str = ""):
        self.record_signal(
            SignalType.preference,
            preference,
            source_meeting_id=meeting_id,
        )

    # ── Parsing helpers ───────────────────────────────────────────────────────

    def _parse_short_term_line(self, line: str) -> Optional[MemoryEntry]:
        match = re.match(
            r"^- \[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]\s+\*\*(\w+)\*\*:\s*(.+)$",
            line,
        )
        if not match:
            return None

        timestamp, signal_type, rest = match.groups()

        # Extract optional context and meeting id
        context = ""
        meeting_id = ""
        ctx_match = re.search(r"— _(.+?)_", rest)
        if ctx_match:
            context = ctx_match.group(1)
            rest = rest[: ctx_match.start()].strip()
        mid_match = re.search(r"\(meeting: `([^`]+)`\)", rest)
        if mid_match:
            meeting_id = mid_match.group(1)
            rest = rest[: mid_match.start()].strip()

        return MemoryEntry(
            timestamp=timestamp,
            signal_type=signal_type,
            content=rest,
            context=context,
            source_meeting_id=meeting_id,
        )

    def _parse_patterns(self, text: str) -> list[PatternEntry]:
        patterns = []
        blocks = re.split(r"(?=^### \[)", text, flags=re.MULTILINE)
        for block in blocks:
            block = block.strip()
            if not block.startswith("### ["):
                continue
            header_match = re.match(r"### \[\w+\]\s*(.+)", block)
            if not header_match:
                continue
            pattern_text = header_match.group(1)

            def _extract(label: str) -> str:
                m = re.search(rf"\*\*{label}:\*\*\s*(.+)", block)
                return m.group(1).strip() if m else ""

            patterns.append(PatternEntry(
                pattern=pattern_text,
                signal_type=_extract("Type"),
                observation_count=int(_extract("Observed").split()[0] or "0"),
                context_scope=_extract("Scope") or "universal",
                first_seen=_extract("First seen"),
                last_seen=_extract("Last seen"),
            ))
        return patterns

    def _parse_rules(self, text: str) -> list[ConfirmedRule]:
        rules = []
        blocks = re.split(r"(?=^### CONFIRMED:)", text, flags=re.MULTILINE)
        for block in blocks:
            block = block.strip()
            if not block.startswith("### CONFIRMED:"):
                continue
            header_match = re.match(r"### CONFIRMED:\s*(.+)", block)
            if not header_match:
                continue
            rule_text = header_match.group(1)

            def _extract(label: str) -> str:
                m = re.search(rf"\*\*{label}:\*\*\s*(.+)", block)
                return m.group(1).strip() if m else ""

            rules.append(ConfirmedRule(
                rule=rule_text,
                signal_type=_extract("Type"),
                promoted_from=_extract("Source pattern").strip("`"),
                promoted_at=_extract("Promoted"),
                context_scope=_extract("Scope") or "universal",
            ))
        return rules

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _path_for_tier(self, tier: MemoryTier) -> Path:
        return {
            MemoryTier.short: self._short_path,
            MemoryTier.medium: self._medium_path,
            MemoryTier.long: self._long_path,
        }[tier]

    def _append_to_file(self, path: Path, line: str):
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


# Module-level singleton
memory = MemoryStore()
