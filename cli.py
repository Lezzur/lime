"""
LIME CLI — Phase 1
Commands: start, stop, status, list, view, devices, server
"""

import sys
import time
import json
import logging
import threading
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich import box

app = typer.Typer(
    name="lime",
    help="LIME — cognitive meeting companion",
    add_completion=False,
)
console = Console()

# Suppress noisy loggers when running CLI
logging.getLogger("faster_whisper").setLevel(logging.WARNING)
logging.getLogger("torch").setLevel(logging.WARNING)
logging.getLogger("pyannote").setLevel(logging.WARNING)


def _bootstrap():
    """Initialize DB before any command that needs it."""
    from backend.storage.database import init_db
    init_db()


# ── start ─────────────────────────────────────────────────────────────────────

@app.command()
def start(
    source: str = typer.Option("microphone", "--source", "-s", help="microphone | system"),
    device: Optional[int] = typer.Option(None, "--device", "-d", help="Audio device index"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Meeting title"),
):
    """Start recording a meeting."""
    _bootstrap()

    if source not in ("microphone", "system"):
        console.print("[red]Error:[/] source must be 'microphone' or 'system'")
        raise typer.Exit(1)

    from backend.audio.capture import AudioSource
    from backend.audio.session import MeetingSession
    from backend.audio.compressor import compressor

    compressor.start()

    src = AudioSource.system if source == "system" else AudioSource.microphone
    live_lines: list[str] = []

    def on_transcript(result):
        ts = f"[{result.start_time:6.1f}s]"
        speaker = ""
        conf_badge = f" [yellow][{result.confidence:.0%}][/]" if result.confidence < 0.7 else ""
        line = f"{ts} {speaker}{result.text}{conf_badge}"
        live_lines.append(line)

    session = MeetingSession(source=src, device_index=device, on_transcript=on_transcript)
    meeting_id = session.start()

    if title:
        from backend.storage.database import get_db
        from backend.models.meeting import Meeting
        with get_db() as db:
            m = db.get(Meeting, meeting_id)
            if m:
                m.title = title

    console.print(Panel(
        f"[bold green]Recording started[/]\n"
        f"Meeting ID : [cyan]{meeting_id}[/]\n"
        f"Source     : [cyan]{source}[/]\n"
        f"[dim]Press Ctrl+C to stop[/]",
        title="LIME",
        border_style="green",
    ))

    try:
        with Live(console=console, refresh_per_second=2) as live:
            while True:
                time.sleep(0.5)
                elapsed = session._capture.elapsed_seconds
                table = Table(box=box.SIMPLE, show_header=False, expand=True)
                table.add_column("", style="dim")
                table.add_column("")
                table.add_row("Elapsed", f"{elapsed:.0f}s")
                table.add_row("Segments", str(len(live_lines)))

                text = Text()
                for line in live_lines[-10:]:  # Show last 10 lines
                    text.append(line + "\n")

                from rich.columns import Columns
                live.update(Panel(text, title=f"Live Transcript — {elapsed:.0f}s", border_style="dim"))

    except KeyboardInterrupt:
        pass
    finally:
        console.print("\n[yellow]Stopping...[/]")
        result = session.stop()
        compressor.stop()
        console.print(Panel(
            f"[bold]Meeting saved[/]\n"
            f"ID       : [cyan]{meeting_id}[/]\n"
            f"Duration : [cyan]{result['duration_seconds']:.1f}s[/]\n"
            f"Run [bold]lime view {meeting_id}[/] to review the transcript.",
            title="Done",
            border_style="green",
        ))


# ── list ──────────────────────────────────────────────────────────────────────

@app.command("list")
def list_meetings(limit: int = typer.Option(20, "--limit", "-n")):
    """List recent meetings."""
    _bootstrap()
    from backend.storage.database import get_db
    from backend.models.meeting import Meeting, TranscriptSegment

    with get_db() as db:
        meetings = (
            db.query(Meeting)
            .order_by(Meeting.started_at.desc())
            .limit(limit)
            .all()
        )

    if not meetings:
        console.print("[dim]No meetings recorded yet.[/]")
        return

    table = Table(title="Meetings", box=box.ROUNDED)
    table.add_column("ID", style="cyan", no_wrap=True, max_width=12)
    table.add_column("Title")
    table.add_column("Source", justify="center")
    table.add_column("Started", no_wrap=True)
    table.add_column("Duration", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("Segments", justify="right")

    for m in meetings:
        mid_short = m.id[:8]
        duration = f"{m.duration_seconds:.0f}s" if m.duration_seconds else "—"
        status_style = {"recording": "yellow", "complete": "green", "failed": "red"}.get(
            m.status.value, "white"
        )
        table.add_row(
            mid_short,
            m.title or "[dim]Untitled[/]",
            m.audio_source.value,
            m.started_at.strftime("%Y-%m-%d %H:%M"),
            duration,
            f"[{status_style}]{m.status.value}[/]",
            str(len(m.segments)),
        )

    console.print(table)


# ── view ──────────────────────────────────────────────────────────────────────

@app.command()
def view(meeting_id: str = typer.Argument(..., help="Meeting ID (or prefix)")):
    """View the transcript for a meeting."""
    _bootstrap()
    from backend.storage.database import get_db
    from backend.models.meeting import Meeting, TranscriptSegment

    with get_db() as db:
        # Support prefix search
        meeting = (
            db.query(Meeting)
            .filter(Meeting.id.startswith(meeting_id))
            .first()
        )
        if not meeting:
            console.print(f"[red]Meeting not found:[/] {meeting_id}")
            raise typer.Exit(1)

        segments = (
            db.query(TranscriptSegment)
            .filter(TranscriptSegment.meeting_id == meeting.id)
            .order_by(TranscriptSegment.start_time)
            .all()
        )

        title = meeting.title or "Untitled Meeting"
        duration = f"{meeting.duration_seconds:.0f}s" if meeting.duration_seconds else "ongoing"

        console.print(Panel(
            f"[bold]{title}[/]\n"
            f"ID: [cyan]{meeting.id}[/]  |  "
            f"Started: {meeting.started_at.strftime('%Y-%m-%d %H:%M')}  |  "
            f"Duration: {duration}  |  "
            f"Source: {meeting.audio_source.value}",
            title="LIME — Meeting",
            border_style="cyan",
        ))

    if not segments:
        console.print("[dim]No transcript segments yet.[/]")
        return

    for seg in segments:
        ts = f"[dim][{seg.start_time:6.1f}s → {seg.end_time:.1f}s][/]"
        speaker = f"[bold magenta]{seg.speaker.name or seg.speaker.label}:[/] " if seg.speaker else ""
        low_conf = f" [yellow][{seg.confidence:.0%}][/]" if seg.is_low_confidence else ""
        lang = f" [dim]({seg.language})[/]" if seg.language and seg.language != "en" else ""
        console.print(f"{ts} {speaker}{seg.text}{low_conf}{lang}")


# ── devices ───────────────────────────────────────────────────────────────────

@app.command()
def devices():
    """List available audio input devices."""
    from backend.audio.capture import list_audio_devices

    devs = list_audio_devices()
    table = Table(title="Audio Devices", box=box.ROUNDED)
    table.add_column("Index", justify="right", style="cyan")
    table.add_column("Name")
    table.add_column("Host API")
    table.add_column("In Ch", justify="right")
    table.add_column("Sample Rate", justify="right")

    for d in devs:
        if d["max_input_channels"] > 0:
            table.add_row(
                str(d["index"]),
                d["name"],
                d["hostapi"],
                str(d["max_input_channels"]),
                f"{d['default_samplerate']:.0f}",
            )

    console.print(table)


# ── server ────────────────────────────────────────────────────────────────────

@app.command()
def server(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
):
    """Start the LIME API server."""
    import uvicorn
    console.print(f"[green]Starting LIME API server[/] → http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=reload)


# ── status ────────────────────────────────────────────────────────────────────

@app.command()
def status():
    """Check server health and DB stats."""
    _bootstrap()
    from backend.storage.database import get_db
    from backend.models.meeting import Meeting, MeetingStatus as MS

    with get_db() as db:
        total = db.query(Meeting).count()
        complete = db.query(Meeting).filter(Meeting.status == MS.complete).count()
        recording = db.query(Meeting).filter(Meeting.status == MS.recording).count()

    console.print(Panel(
        f"Meetings total    : [cyan]{total}[/]\n"
        f"  Complete        : [green]{complete}[/]\n"
        f"  Recording now   : [yellow]{recording}[/]",
        title="LIME Status",
        border_style="blue",
    ))


if __name__ == "__main__":
    app()
