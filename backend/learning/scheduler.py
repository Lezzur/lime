"""
Memory consolidation scheduler.

Automatically runs the consolidation engine during idle periods.

Rules:
  - At most once per day.
  - Only during idle time (no active meetings or processing).
  - If no idle window opens, forced run after 14 days regardless.
  - Persists last-run timestamp to survive restarts.
  - Never interrupts user activity (except the biweekly forced fallback).
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from backend.config.settings import settings
from backend.learning.consolidation import ConsolidationEngine, consolidator

logger = logging.getLogger(__name__)

_STATE_FILENAME = ".consolidation_state.json"


class ConsolidationScheduler:
    """
    Background daemon that monitors system idle state and triggers
    memory consolidation on the appropriate schedule.
    """

    def __init__(
        self,
        engine: Optional[ConsolidationEngine] = None,
        idle_checker: Optional[Callable[[], bool]] = None,
        check_interval_seconds: float = 60.0,
        max_daily_runs: int = 1,
        forced_interval_days: int = 14,
        state_dir: Optional[Path] = None,
    ):
        self._engine = engine or consolidator
        self._idle_checker = idle_checker or _default_idle_checker
        self._check_interval = check_interval_seconds
        self._max_daily_runs = max_daily_runs
        self._forced_interval = timedelta(days=forced_interval_days)
        self._state_dir = state_dir or settings.memory_dir

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_run: Optional[datetime] = None
        self._runs_today: int = 0
        self._today_date: Optional[str] = None
        self._last_stats: Optional[dict] = None

        self._load_state()

    # ── Public interface ─────────────────────────────────────────────────────

    def start(self):
        """Start the background scheduler thread."""
        if self._running:
            logger.warning("Consolidation scheduler already running.")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="consolidation-scheduler"
        )
        self._thread.start()
        logger.info(
            "Consolidation scheduler started. "
            f"Check interval: {self._check_interval}s, "
            f"forced fallback: {self._forced_interval.days} days."
        )

    def stop(self):
        """Stop the scheduler gracefully."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10.0)
            self._thread = None
        self._save_state()
        logger.info("Consolidation scheduler stopped.")

    def status(self) -> dict:
        """Return current scheduler status for monitoring/API."""
        now = datetime.now(timezone.utc)
        next_forced = None
        if self._last_run:
            next_forced = (self._last_run + self._forced_interval).isoformat()

        since_last = None
        if self._last_run:
            since_last = (now - self._last_run).total_seconds()

        return {
            "running": self._running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "seconds_since_last_run": round(since_last, 1) if since_last else None,
            "runs_today": self._runs_today,
            "max_daily_runs": self._max_daily_runs,
            "forced_deadline": next_forced,
            "forced_interval_days": self._forced_interval.days,
            "is_idle": self._idle_checker(),
            "last_stats": self._last_stats,
        }

    def force_run(self) -> dict:
        """Manually trigger a consolidation run, bypassing idle/schedule checks."""
        logger.info("Forced consolidation triggered.")
        return self._execute()

    # ── Core loop ────────────────────────────────────────────────────────────

    def _loop(self):
        # Small initial delay to let the server finish starting up
        time.sleep(5.0)

        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.error(f"Consolidation scheduler error: {e}", exc_info=True)

            # Sleep in small increments so stop() is responsive
            slept = 0.0
            while slept < self._check_interval and self._running:
                time.sleep(min(2.0, self._check_interval - slept))
                slept += 2.0

    def _tick(self):
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")

        # Reset daily counter on new day
        if today != self._today_date:
            self._today_date = today
            self._runs_today = 0

        # Check if already hit daily limit
        if self._runs_today >= self._max_daily_runs:
            return

        # Check if forced run is overdue (biweekly guarantee)
        forced_overdue = False
        if self._last_run is None:
            # Never run before — treat as overdue after a grace period
            forced_overdue = True
        elif (now - self._last_run) >= self._forced_interval:
            forced_overdue = True

        if forced_overdue:
            # Even forced runs skip if there are no signals at all
            short_entries = self._engine.store.read_short_term_entries()
            if not short_entries:
                return
            logger.info(
                "Consolidation forced: "
                f"{'never run before' if self._last_run is None else f'{self._forced_interval.days}-day deadline reached'} "
                f"({len(short_entries)} pending signals)."
            )
            self._execute()
            return

        # Normal path: only consolidate during idle time
        if not self._idle_checker():
            return

        # Check there are actually signals to process
        short_entries = self._engine.store.read_short_term_entries()
        if not short_entries:
            return

        logger.info(
            f"System idle with {len(short_entries)} pending signals. "
            "Starting consolidation."
        )
        self._execute()

    def _execute(self) -> dict:
        """Run the consolidation engine and update bookkeeping."""
        stats = self._engine.run()

        if stats.get("skipped"):
            logger.info("Consolidation skipped (already in progress).")
            return stats

        now = datetime.now(timezone.utc)
        self._last_run = now
        self._runs_today += 1
        self._last_stats = stats
        self._save_state()

        logger.info(f"Consolidation complete. Stats: {stats}")
        return stats

    # ── State persistence ────────────────────────────────────────────────────

    def _state_path(self) -> Path:
        return self._state_dir / _STATE_FILENAME

    def _load_state(self):
        path = self._state_path()
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("last_run"):
                self._last_run = datetime.fromisoformat(data["last_run"])
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if data.get("today_date") == today:
                self._runs_today = data.get("runs_today", 0)
            self._today_date = today
            self._last_stats = data.get("last_stats")
            logger.info(
                f"Consolidation state loaded. Last run: {self._last_run or 'never'}"
            )
        except Exception as e:
            logger.warning(f"Failed to load consolidation state: {e}")

    def _save_state(self):
        path = self._state_path()
        data = {
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "today_date": self._today_date,
            "runs_today": self._runs_today,
            "last_stats": self._last_stats,
        }
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save consolidation state: {e}")


# ── Idle detection ───────────────────────────────────────────────────────────

# Registry of activity indicators. Other modules register themselves here.
# Each callable returns True if that subsystem is currently busy.
_activity_indicators: list[Callable[[], bool]] = []


def register_activity_indicator(indicator: Callable[[], bool]):
    """
    Register a function that returns True when its subsystem is busy.
    The scheduler considers the system idle only when ALL indicators return False.

    Usage from other modules:
        from backend.learning.scheduler import register_activity_indicator
        register_activity_indicator(lambda: len(active_sessions) > 0)
    """
    _activity_indicators.append(indicator)
    logger.debug(f"Activity indicator registered (total: {len(_activity_indicators)})")


def _default_idle_checker() -> bool:
    """
    Returns True when the system is idle (no subsystem is busy).
    If no indicators are registered, assumes idle.
    """
    for indicator in _activity_indicators:
        try:
            if indicator():
                return False  # At least one subsystem is busy
        except Exception as e:
            logger.warning(f"Activity indicator error: {e}")
    return True


# ── Module-level singleton ───────────────────────────────────────────────────

scheduler = ConsolidationScheduler(
    check_interval_seconds=settings.consolidation_check_interval,
    max_daily_runs=settings.consolidation_max_daily_runs,
    forced_interval_days=settings.consolidation_forced_interval_days,
)
