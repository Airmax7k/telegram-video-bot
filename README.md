# telegram-video-bot — IA de génération d'images et de vidéos

Bot Telegram qui génère des images et de courtes vidéos à partir d'une description, **gratuitement**.

## Fonctionnalités

- Envoie une description → le bot renvoie l'image générée
- Styles : `photo`, `anime`, `art`, `3d`, `pixel`, `aquarelle`
- Formats : `carre`, `portrait`, `paysage`
- Bouton « 🔄 Nouvelle variante » pour régénérer
- Vidéos gratuites : `/video` crée 3 scènes IA animées (zoom, panoramique, fondus) en ~8 s de vidéo ; le bouton « 🎬 Animer » anime une image déjà générée
- 3 moteurs au choix :
  - **pollinations** (par défaut) : gratuit, aucune clé API
  - **openai** : `gpt-image-1` (clé `OPENAI_API_KEY`)
  - **huggingface** : FLUX.1-schnell ou autre modèle (jeton `HF_API_TOKEN`)

## Installation

1. Crée un bot avec [@BotFather](https://t.me/BotFather) et récupère le jeton.
2. Configure :
   ```bash
   cp .env.example .env   # puis renseigne TELEGRAM_BOT_TOKEN
   pip install -r requirements.txt
   ```
3. Installe **ffmpeg** (nécessaire pour les vidéos) : `sudo apt install ffmpeg`, `brew install ffmpeg` ou https://ffmpeg.org/download.html
4. Lance :
   ```bash
   python -m imagebot.bot
   ```

Avec Docker :
```bash
docker build -t imagebot .
docker run --env-file .env imagebot
```

## Utilisation

| Commande | Effet |
|---|---|
| *(texte libre)* | génère une image |
| `/imagine <description>` | génère une image |
| `/video <description>` | génère une courte vidéo animée (~30 à 60 s d'attente) |
| `/style` | choisir un style par défaut |
| `/taille` | choisir le format |
| `/help` | aide |

Options dans le message : `un dragon au-dessus de Paris --style art --taille paysage --seed 42`

## À propos de la gratuité

Le moteur **pollinations** est gratuit et sans clé, mais limité à environ une image toutes les 15 secondes : le bot attend et réessaie automatiquement. Les images portent un petit logo « pollinations.ai ».

Les vraies IA vidéo (Veo, Sora, Kling, Wan…) sont toutes payantes. Le bot fabrique donc ses vidéos lui-même avec ffmpeg à partir d'images IA : c'est 100 % gratuit, mais ce sont des images animées, pas des scènes filmées.

Pour limiter l'accès, mets les IDs Telegram autorisés dans `ALLOWED_USER_IDS`.

## Tests

```bash
pip install pytest && python -m pytest
```
