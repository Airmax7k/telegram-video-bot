"""Moteurs de génération d'images (text-to-image)."""

from __future__ import annotations

import base64
import random
import re
from dataclasses import dataclass
from urllib.parse import quote

import httpx

STYLES: dict[str, str] = {
    "photo": "photorealistic, highly detailed, natural lighting, 35mm photography",
    "anime": "anime style, vibrant colors, clean line art, studio quality",
    "art": "digital painting, artstation, concept art, dramatic lighting",
    "3d": "3d render, octane render, soft shadows, high detail",
    "pixel": "pixel art, 16-bit, retro video game style",
    "aquarelle": "watercolor painting, soft edges, paper texture",
}

SIZES: dict[str, tuple[int, int]] = {
    "carre": (1024, 1024),
    "portrait": (1024, 1536),
    "paysage": (1536, 1024),
}


class GenerationError(Exception):
    """Erreur lisible par l'utilisateur lors de la génération."""


@dataclass
class ImageRequest:
    prompt: str
    style: str | None = None
    size: str = "carre"
    seed: int | None = None

    def full_prompt(self) -> str:
        if self.style and self.style in STYLES:
            return f"{self.prompt}, {STYLES[self.style]}"
        return self.prompt

    @property
    def dimensions(self) -> tuple[int, int]:
        return SIZES.get(self.size, SIZES["carre"])


_OPTION_RE = re.compile(r"--(style|taille|seed)\s+(\S+)", re.IGNORECASE)


def parse_prompt(text: str, default_style: str | None = None, default_size: str = "carre") -> ImageRequest:
    """Extrait les options `--style`, `--taille` et `--seed` d'un texte libre."""
    req = ImageRequest(prompt="", style=default_style, size=default_size)
    for key, value in _OPTION_RE.findall(text):
        key, value = key.lower(), value.lower()
        if key == "style":
            if value not in STYLES:
                raise GenerationError(f"Style inconnu « {value} ». Choix : {', '.join(STYLES)}")
            req.style = value
        elif key == "taille":
            if value not in SIZES:
                raise GenerationError(f"Taille inconnue « {value} ». Choix : {', '.join(SIZES)}")
            req.size = value
        elif key == "seed":
            if not value.isdigit():
                raise GenerationError("Le seed doit être un nombre entier positif.")
            req.seed = int(value)
    req.prompt = " ".join(_OPTION_RE.sub("", text).split())
    if not req.prompt:
        raise GenerationError("Décris l'image que tu veux, par ex. : un chat astronaute sur la lune")
    if len(req.prompt) > 1000:
        raise GenerationError("Description trop longue (1000 caractères max).")
    return req


class ImageProvider:
    name = "base"

    async def generate(self, req: ImageRequest) -> bytes:
        raise NotImplementedError


class PollinationsProvider(ImageProvider):
    """API publique gratuite, aucune clé requise."""

    name = "pollinations"
    BASE_URL = "https://image.pollinations.ai/prompt/"

    def __init__(self, model: str = "flux", timeout: float = 120.0):
        self.model = model
        self.timeout = timeout

    async def generate(self, req: ImageRequest) -> bytes:
        width, height = req.dimensions
        params = {
            "width": width,
            "height": height,
            "model": self.model,
            "seed": req.seed if req.seed is not None else random.randint(0, 2**31 - 1),
            "nologo": "true",
        }
        url = self.BASE_URL + quote(req.full_prompt(), safe="")
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
        if resp.status_code != 200 or not resp.headers.get("content-type", "").startswith("image/"):
            raise GenerationError(f"Le service d'images a répondu {resp.status_code}. Réessaie dans un instant.")
        return resp.content


class OpenAIProvider(ImageProvider):
    name = "openai"
    URL = "https://api.openai.com/v1/images/generations"

    def __init__(self, api_key: str, model: str = "gpt-image-1", timeout: float = 180.0):
        if not api_key:
            raise ValueError("OPENAI_API_KEY est requis pour le moteur openai")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def generate(self, req: ImageRequest) -> bytes:
        width, height = req.dimensions
        payload = {"model": self.model, "prompt": req.full_prompt(), "size": f"{width}x{height}", "n": 1}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self.URL, json=payload, headers=headers)
            if resp.status_code != 200:
                try:
                    message = resp.json()["error"]["message"]
                except (ValueError, KeyError, TypeError):
                    message = resp.text[:200]
                raise GenerationError(f"OpenAI : {message}")
            data = resp.json()["data"][0]
            if data.get("b64_json"):
                return base64.b64decode(data["b64_json"])
            img = await client.get(data["url"])
            img.raise_for_status()
            return img.content


class HuggingFaceProvider(ImageProvider):
    name = "huggingface"
    URL = "https://router.huggingface.co/hf-inference/models/{model}"

    def __init__(self, api_token: str, model: str = "black-forest-labs/FLUX.1-schnell", timeout: float = 180.0):
        if not api_token:
            raise ValueError("HF_API_TOKEN est requis pour le moteur huggingface")
        self.api_token = api_token
        self.model = model
        self.timeout = timeout

    async def generate(self, req: ImageRequest) -> bytes:
        width, height = req.dimensions
        parameters: dict[str, int] = {"width": width, "height": height}
        if req.seed is not None:
            parameters["seed"] = req.seed
        payload = {"inputs": req.full_prompt(), "parameters": parameters}
        headers = {"Authorization": f"Bearer {self.api_token}", "Accept": "image/png"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self.URL.format(model=self.model), json=payload, headers=headers)
        if resp.status_code == 503:
            raise GenerationError("Le modèle est en cours de chargement, réessaie dans ~30 secondes.")
        if resp.status_code != 200 or not resp.headers.get("content-type", "").startswith("image/"):
            raise GenerationError(f"Hugging Face a répondu {resp.status_code} : {resp.text[:200]}")
        return resp.content


def build_provider(name: str, env: dict[str, str]) -> ImageProvider:
    name = (name or "pollinations").lower()
    if name == "pollinations":
        return PollinationsProvider()
    if name == "openai":
        return OpenAIProvider(env.get("OPENAI_API_KEY", ""), env.get("OPENAI_IMAGE_MODEL") or "gpt-image-1")
    if name == "huggingface":
        return HuggingFaceProvider(
            env.get("HF_API_TOKEN", ""), env.get("HF_IMAGE_MODEL") or "black-forest-labs/FLUX.1-schnell"
        )
    raise ValueError(f"Moteur inconnu : {name} (pollinations, openai, huggingface)")
