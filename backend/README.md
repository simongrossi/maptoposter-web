# Backend Documentation 🐍

Le backend est divise en deux processus qui partagent le meme code source :

1. **API** (`uvicorn backend.main:app`) : leger, gere les requetes HTTP, les
   sessions anonymes, les quotas et les URLs signees.
2. **Worker** (`celery -A backend.tasks worker`) : lourd, gere OSM, Matplotlib
   et les uploads S3.

## 📂 Structure

| Fichier | Responsabilite |
|---|---|
| `main.py` | Point d'entree FastAPI. Routes `/generate`, `/tasks`, `/download`, `/history`, `/themes`, `/geocode`, `/health`, `/ready`. Sessions, quotas, streaming signe. |
| `settings.py` | Chargement et validation de la configuration. Refuse de demarrer si un secret manque. |
| `security.py` | Signature HMAC des sessions et des URLs de telechargement. |
| `storage.py` | Client S3 (boto3), creation du bucket, upload, listing, retention. |
| `redis_client.py` | Client Redis partage. |
| `models.py` | Validation Pydantic stricte (plafonds memoire/rendu). |
| `tasks.py` | Tache Celery `generate_poster_task`, cache S3, historique, liberation des slots. |
| `celery_app.py` | Configuration Celery/Sentry. |
| `fetcher.py` | AsyncIO + OSMnx : graphe et geometries, cache disque. |
| `renderer.py` | Matplotlib oriente objet, thread-safe, `parse_math=False`. |
| `utils.py` | Themes, polices, geocodage, slugs. |
| `cache.py` | Cache disque atomique (SHA-256). |

## 🔒 Invariants de securite

- Aucune valeur secrete par defaut : `settings.py` leve une `ConfigError` si
  `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `SESSION_SECRET`,
  `DOWNLOAD_SIGNING_SECRET` ou `REDIS_URL` manquent.
- Le bucket S3 est prive. Le worker renvoie une **cle d'objet**, jamais une URL
  publique ; l'API construit l'URL signee.
- Le style de theme est filtre par `^[a-z0-9_]{1,64}$` et le chemin resolu est
  verifie comme etant sous `themes/`.
- Toute entree est validee par Pydantic, avec `extra="forbid"`.
- Le worker ne depasse pas 2 Go (cgroup Docker) et est recycle apres chaque
  tache.

## 🛠️ Ajouter un theme

1. Creer un fichier JSON dans `/themes` (ex: `cyberpunk.json`).
2. Definir `name`, `bg`, `text`, `gradient_color`, `water`, `parks` et les
   couleurs `road_*`.
3. Le theme est automatiquement detecte par `GET /themes` et par le fichier
   `themes/` copie dans l'image.

## ⚠️ Points critiques

- **Matplotlib** : toujours utiliser l'API objet (`Figure`), fermer/clear la
  figure et laisser le worker recycler le processus apres chaque tache.
- **S3** : utiliser `backend/storage.py`, jamais boto3 directement dans les
  routes. Le bucket est cree au demarrage.
- **URLs** : ne jamais renvoyer `file_key` au navigateur ; uniquement
  `file_url` signee via `build_download_url()`.
- **Erreurs** : ne jamais renvoyer `str(exception)` au client ; utiliser
  `_public_error()` et journaliser cote serveur.

## 🧪 Tests

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Les tests d'API injectent un faux Redis et une fausse tache Celery
(`tests/backend/conftest.py`). Les tests de rendu sont ignores si les
dependances lourdes (Matplotlib/OSMnx) ne sont pas installees.
