"""VoiceMorph engine CLI (``voicemorph``).

Proves the engine end-to-end from the command line before any app layer:

    voicemorph profile create --name "Alex" --subject "Alex" --self --confirm
    voicemorph preprocess ./raw_alex_audio <voice_id>
    voicemorph train <voice_id> --epochs 200
    voicemorph convert <voice_id> input.mp4 output.mp4   # video in → video out
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from voicemorph_engine.backends import get_backend
from voicemorph_engine.backends.base import ConversionParams, TrainingParams
from voicemorph_engine.config import EngineConfig
from voicemorph_engine.errors import VoiceMorphError
from voicemorph_engine.profiles import (
    ConsentMethod,
    ConsentRecord,
    ProfileRegistry,
    ProfileStatus,
)

app = typer.Typer(help="VoiceMorph voice-conversion engine", no_args_is_help=True)
profile_app = typer.Typer(help="Manage voice profiles")
app.add_typer(profile_app, name="profile")
console = Console()


def _config() -> EngineConfig:
    cfg = EngineConfig()
    cfg.ensure_dirs()
    return cfg


def _registry(cfg: EngineConfig) -> ProfileRegistry:
    return ProfileRegistry(cfg.profiles_dir)


# --------------------------------------------------------------------------
# profile
# --------------------------------------------------------------------------

@profile_app.command("create")
def profile_create(
    name: str = typer.Option(..., help="Display name for the voice profile."),
    subject: str = typer.Option(..., help="Whose voice this is."),
    granted_by: str | None = typer.Option(None, help="Who granted consent (defaults to subject)."),
    self_voice: bool = typer.Option(False, "--self", help="This is your own voice."),
    method: ConsentMethod = typer.Option(ConsentMethod.SELF, help="Consent method."),
    reference: str | None = typer.Option(None, help="Consent artifact reference."),
    confirm: bool = typer.Option(
        False, "--confirm", help="Confirm you have the right to use this voice (REQUIRED)."
    ),
):
    """Create a voice profile. Requires an explicit consent confirmation."""
    cfg = _config()
    reg = _registry(cfg)
    consent = ConsentRecord(
        subject=subject,
        granted_by=granted_by or subject,
        method=ConsentMethod.SELF if self_voice else method,
        reference=reference,
        confirmed=confirm,
    )
    try:
        profile = reg.create(
            name=name, consent=consent, backend=cfg.backend, sample_rate=cfg.sample_rate
        )
    except VoiceMorphError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    console.print(
        f"[green]Created profile[/green] [bold]{profile.name}[/bold] → {profile.voice_id}"
    )


@profile_app.command("list")
def profile_list():
    cfg = _config()
    reg = _registry(cfg)
    table = Table(title="Voice profiles")
    for col in ("voice_id", "name", "status", "subject", "ready"):
        table.add_column(col)
    for p in reg.list():
        table.add_row(
            p.voice_id, p.name, p.status.value, p.consent.subject, "✓" if p.is_ready else ""
        )
    console.print(table)


@profile_app.command("delete")
def profile_delete(voice_id: str):
    cfg = _config()
    _registry(cfg).delete(voice_id)
    console.print(f"[yellow]Deleted[/yellow] {voice_id}")


# --------------------------------------------------------------------------
# preprocess
# --------------------------------------------------------------------------

@app.command()
def preprocess(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    voice_id: str = typer.Argument(..., help="Target profile id."),
):
    """Preprocess raw recordings into training clips inside the profile dir."""
    from voicemorph_engine.preprocessing import preprocess_dataset

    cfg = _config()
    reg = _registry(cfg)
    profile = reg.get(voice_id)
    dataset_dir = reg.profile_dir(voice_id) / "dataset"

    profile.status = ProfileStatus.PREPROCESSING
    reg.save(profile)
    report = preprocess_dataset(input_dir, dataset_dir)
    profile.status = ProfileStatus.CREATED
    profile.metadata["dataset_seconds"] = round(report.total_seconds, 2)
    reg.save(profile)

    console.print(
        f"[green]Preprocessed[/green] {report.input_files} files → "
        f"{report.clips_written} clips ({report.total_seconds:.1f}s) at {dataset_dir}"
    )


# --------------------------------------------------------------------------
# train
# --------------------------------------------------------------------------

@app.command()
def train(
    voice_id: str = typer.Argument(...),
    epochs: int = typer.Option(200),
    batch_size: int = typer.Option(8),
):
    """Train the voice model from the profile's preprocessed dataset."""
    cfg = _config()
    reg = _registry(cfg)
    profile = reg.get(voice_id)
    dataset_dir = reg.profile_dir(voice_id) / "dataset"
    if not dataset_dir.exists():
        console.print("[red]No dataset. Run 'voicemorph preprocess' first.[/red]")
        raise typer.Exit(code=2)

    backend = get_backend(cfg)
    params = TrainingParams(epochs=epochs, batch_size=batch_size, sample_rate=cfg.sample_rate)
    profile.status = ProfileStatus.TRAINING
    reg.save(profile)
    try:
        result = backend.train(
            voice_id=voice_id,
            dataset_dir=dataset_dir,
            output_dir=reg.profile_dir(voice_id),
            params=params,
        )
    except VoiceMorphError as exc:
        profile.status = ProfileStatus.FAILED
        profile.error = str(exc)
        reg.save(profile)
        console.print(f"[red]Training failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    profile.status = ProfileStatus.READY
    profile.model_path = result.model_path
    profile.index_path = result.index_path
    profile.error = None
    reg.save(profile)
    console.print(f"[green]Trained[/green] {voice_id} → {result.model_path}")


# --------------------------------------------------------------------------
# convert (media-aware: video in → video out, audio in → audio out)
# --------------------------------------------------------------------------

@app.command()
def convert(
    voice_id: str = typer.Argument(...),
    source: Path = typer.Argument(..., exists=True, dir_okay=False),
    output: Path = typer.Argument(...),
    transpose: int = typer.Option(0, help="Semitone shift (0 = keep source register)."),
    index_rate: float = typer.Option(0.75),
    protect: float = typer.Option(0.33),
):
    """Convert audio or video to the target voice, preserving timing and (for video) visuals."""
    cfg = _config()
    reg = _registry(cfg)
    profile = reg.get(voice_id)
    if not profile.is_ready:
        console.print(
            f"[red]Profile {voice_id} is not trained (status={profile.status.value}).[/red]"
        )
        raise typer.Exit(code=2)

    backend = get_backend(cfg)
    backend.load_voice(
        voice_id,
        Path(profile.model_path),
        Path(profile.index_path) if profile.index_path else None,
    )
    params = ConversionParams(transpose=transpose, index_rate=index_rate, protect=protect)

    # Route via the media layer: it detects audio-vs-video and handles
    # extract → convert → remux (video stream bit-identical) for video inputs.
    from voicemorph_media.pipeline import convert_media

    try:
        result = convert_media(
            source=source,
            output=output,
            convert_audio=lambda a, o: backend.convert_file(voice_id, a, o, params),
            work_dir=cfg.artifacts_dir,
            sample_rate=cfg.sample_rate,
        )
    except VoiceMorphError as exc:
        console.print(f"[red]Conversion failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]Wrote[/green] {output} ({result.kind}, {result.duration:.2f}s)")


# --------------------------------------------------------------------------
# info (hardware + auto-selected backend)
# --------------------------------------------------------------------------

@app.command()
def info():
    """Show detected hardware and the backend VoiceMorph would auto-select."""
    from voicemorph_engine.hardware import probe

    cfg = _config()
    hw = probe(cfg.device)
    table = Table(title="VoiceMorph hardware")
    table.add_column("property")
    table.add_column("value")
    table.add_row("device (resolved)", hw.device)
    table.add_row("CUDA GPU", "✓ " + (hw.gpu or "") if hw.cuda else "✗ (CPU only)")
    table.add_row("configured backend", cfg.backend)
    table.add_row("auto → backend", hw.recommended_backend)
    table.add_row("available backends", ", ".join(hw.available_backends) or "-")
    console.print(table)
    console.print(
        "[dim]Override with --device / VOICEMORPH_DEVICE and "
        "VOICEMORPH_ENGINE_BACKEND (e.g. rvc, freevc, speecht5, passthrough).[/dim]"
    )


if __name__ == "__main__":
    app()
