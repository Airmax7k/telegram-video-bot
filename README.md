# telegram-video-bot — IA de génération d'images

Bot Telegram qui génère des images à partir d'une description (text-to-image).

## Fonctionnalités

- Envoie une description → le bot renvoie l'image générée
- Styles : `photo`, `anime`, `art`, `3d`, `pixel`, `aquarelle`
- Formats : `carre`, `portrait`, `paysage`
- Bouton « 🔄 Nouvelle variante » pour régénérer
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
3. Lance :
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
| `/style` | choisir un style par défaut |
| `/taille` | choisir le format |
| `/help` | aide |

Options dans le message : `un dragon au-dessus de Paris --style art --taille paysage --seed 42`

Pour limiter l'accès, mets les IDs Telegram autorisés dans `ALLOWED_USER_IDS`.

## Tests

```bash
pip install pytest && python -m pytest
```
