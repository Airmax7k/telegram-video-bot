import asyncio
import subprocess

import pytest

from imagebot.generator import ImageProvider, ImageRequest
from imagebot.video import build_filter, ffmpeg_available, generate_video

pytestmark = pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg requis")


def _png(color: str) -> bytes:
    return subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", f"color={color}:s=320x320",
         "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "-"],
        check=True, capture_output=True,
    ).stdout


class FakeProvider(ImageProvider):
    def __init__(self):
        self.seeds = []

    async def generate(self, req: ImageRequest) -> bytes:
        self.seeds.append(req.seed)
        return _png(["red", "green", "blue"][len(self.seeds) % 3])


def test_build_filter_chains_crossfades():
    graph, output = build_filter(3, 768, 768, 3.5)
    assert graph.count("zoompan") == 3
    assert graph.count("xfade") == 2
    assert output == "x2"


def test_generate_video_produces_mp4():
    provider = FakeProvider()
    clip = asyncio.run(generate_video(provider, ImageRequest(prompt="test", seed=10, size="paysage"), scenes=2))
    assert clip[4:8] == b"ftyp"
    assert provider.seeds == [10, 11]
