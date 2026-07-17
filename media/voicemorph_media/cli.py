"""``voicemorph-media`` CLI — inspect and exercise the media layer without the engine."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from voicemorph_media.ffmpeg import ensure_ffmpeg, extract_audio, probe, remux_audio

app = typer.Typer(help="VoiceMorph media I/O utilities", no_args_is_help=True)
console = Console()


@app.command()
def check():
    """Verify ffmpeg/ffprobe are installed and on PATH."""
    ensure_ffmpeg()
    console.print("[green]ffmpeg and ffprobe are available.[/green]")


@app.command(name="probe")
def probe_cmd(path: Path = typer.Argument(..., exists=True, dir_okay=False)):
    """Show container/stream info for a media file."""
    info = probe(path)
    console.print(
        f"[bold]{info.path.name}[/bold]  format={info.format_name}  duration={info.duration:.2f}s"
    )
    console.print(f"kind: [cyan]{'video' if info.is_video else 'audio'}[/cyan]")
    table = Table("index", "type", "codec", "duration")
    for s in info.streams:
        dur = f"{s.duration:.2f}" if s.duration else "-"
        table.add_row(str(s.index), s.codec_type, s.codec_name, dur)
    console.print(table)


@app.command()
def extract(
    source: Path = typer.Argument(..., exists=True, dir_okay=False),
    output: Path = typer.Argument(...),
    sample_rate: int = typer.Option(40_000),
):
    """Extract the audio track to a canonical mono WAV."""
    extract_audio(source, output, sample_rate=sample_rate, channels=1)
    console.print(f"[green]Extracted[/green] → {output}")


@app.command()
def remux(
    video: Path = typer.Argument(..., exists=True, dir_okay=False),
    audio: Path = typer.Argument(..., exists=True, dir_okay=False),
    output: Path = typer.Argument(...),
):
    """Remux an audio track into a video (video copied bit-identical)."""
    remux_audio(video, audio, output)
    console.print(f"[green]Remuxed[/green] → {output}")


if __name__ == "__main__":
    app()
