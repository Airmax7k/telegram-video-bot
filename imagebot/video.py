"""Création de vidéos gratuites : images IA animées localement avec ffmpeg."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

from imagebot.generator import GenerationError, ImageProvider, ImageRequest

# Résolution des vidéos (paires, légères pour Telegram)
VIDEO_SIZES: dict[str, tuple[int, int]] = {
    "carre": (768, 768),
    "portrait": (576, 1024),
    "paysage": (1024, 576),
}

FPS = 25
TRANSITION = 1.0  # durée des fondus enchaînés, en secondes

# Mouvements de caméra (zoom, x, y) appliqués tour à tour à chaque image
_MOVES = [
    ("min(zoom+0.0015,1.35)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),  # zoom avant au centre
    ("if(eq(on,0),1.35,max(zoom-0.0015,1))", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),  # zoom arrière
    ("1.25", "(iw-iw/zoom)*on/{frames}", "ih/2-(ih/zoom/2)"),  # panoramique gauche → droite
    ("1.25", "(iw-iw/zoom)*(1-on/{frames})", "ih/2-(ih/zoom/2)"),  # panoramique droite → gauche
]


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def build_filter(count: int, width: int, height: int, seconds: float) -> tuple[str, str]:
    """Construit le filtre ffmpeg (mouvement de caméra + fondus) et renvoie (filtre, sortie)."""
    frames = int(seconds * FPS)
    parts = []
    for i in range(count):
        zoom, x, y = _MOVES[i % len(_MOVES)]
        parts.append(
            f"[{i}:v]scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
            f"crop={width * 2}:{height * 2},"
            f"zoompan=z='{zoom}':x='{x.format(frames=frames)}':y='{y.format(frames=frames)}'"
            f":d={frames}:s={width}x{height}:fps={FPS},setsar=1,format=yuv420p[v{i}]"
        )
    last = "v0"
    for i in range(1, count):
        offset = i * (seconds - TRANSITION)
        out = f"x{i}"
        parts.append(f"[{last}][v{i}]xfade=transition=fade:duration={TRANSITION}:offset={offset:.2f}[{out}]")
        last = out
    return ";".join(parts), last


async def images_to_video(images: list[bytes], size: str = "carre", seconds_per_image: float = 3.5) -> bytes:
    """Assemble des images en une vidéo MP4 animée."""
    if not images:
        raise ValueError("Aucune image à animer")
    if not ffmpeg_available():
        raise GenerationError("ffmpeg n'est pas installé sur le serveur du bot.")
    width, height = VIDEO_SIZES.get(size, VIDEO_SIZES["carre"])
    filter_graph, output = build_filter(len(images), width, height, seconds_per_image)

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        args = ["ffmpeg", "-y", "-loglevel", "error"]
        for i, data in enumerate(images):
            path = tmpdir / f"img{i}"
            path.write_bytes(data)
            args += ["-i", str(path)]
        out_path = tmpdir / "video.mp4"
        args += [
            "-filter_complex", filter_graph, "-map", f"[{output}]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg a échoué : {stderr.decode(errors='replace')[-500:]}")
        return out_path.read_bytes()


async def generate_video(provider: ImageProvider, req: ImageRequest, scenes: int = 3) -> bytes:
    """Génère plusieurs variantes IA de la description puis les anime en vidéo."""
    images = []
    for i in range(scenes):
        # Requêtes séquentielles : l'offre gratuite limite les appels simultanés
        scene = ImageRequest(
            prompt=req.prompt,
            style=req.style,
            size=req.size,
            seed=None if req.seed is None else req.seed + i,
        )
        images.append(await provider.generate(scene))
    return await images_to_video(images, req.size)
