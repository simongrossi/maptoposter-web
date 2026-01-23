# Backend Documentation 🐍

Le backend est divisé en deux processus distincts qui partagent le même code source mais s'exécutent différemment :
1. **API** (`uvicorn backend.main:app`) : Leger, gère les requêtes HTTP.
2. **Worker** (`celery -A backend.tasks worker`) : Lourd, gère OSM et Matplotlib.

## 📂 Structure des Fichiers

| Fichier | Responsabilité |
|---------|----------------|
| `main.py` | Point d'entrée FastAPI. Routes `/generate`, `/tasks`, `/themes` et `/geocode` (Proxy). Gère le Rate Limiting et Sentry. |
| `tasks.py` | Point d'entrée Celery. Contient la logique principale `generate_poster_task`. Gère le cache S3 et l'Upload. |
| `celery_app.py` | Configuration de la connexion Redis et Sentry pour le worker. |
| `fetcher.py` | **AsyncIO**. Utilise `osmnx` pour télécharger les graphes et géometries en parallèle. |
| `renderer.py` | **Matplotlib (OO)**. Dessine la carte. Doit être strictement thread-safe (via `Figure` et non `pyplot.state`). |
| `utils.py` | Héhelpers (Geocoding, chargement des thèmes JSON, chargement des polices). |
| `models.py` | Modèles Pydantic pour la validation stricte des entrées/sorties. |

## 🛠️ Ajouter un nouveau style de carte

1. Créer un fichier JSON dans `/themes` (ex: `cyberpunk.json`).
2. Définir les couleurs (`bg`, `water`, `roads`, `text`).
3. Le style sera automatiquement détecté par l'endpoint `GET /themes` (si monté dans le container) ou via l'import statique.

## ⚠️ Points Critiques

- **Matplotlib** : Ne jamais utiliser `plt.plot()` directement dans le code global. Toujours instancier `fig = Figure()`. Toujours appeler `plt.close(fig)` ou `fig.clf()` à la fin pour éviter les fuites de mémoire.
- **S3 Upload** : On utilise `io.BytesIO` pour ne jamais toucher le disque dur du worker. Performance I/O maximale.
