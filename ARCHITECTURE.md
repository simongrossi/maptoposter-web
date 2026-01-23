# Architecture Technique (Antigravity v2)

Ce document décrit le fonctionnement interne de **MapPoster**, conçu selon une architecture Microservices Asynchrone.

## 🔄 Flux de Données (Lifecycle)

### 1. Initialisation (Frontend)
- L'utilisateur configure son affiche sur le Frontend (SvelteKit).
- `SidebarControls.svelte` maintient l'état.
- `MapSelector.svelte` met à jour la prévisualisation (Provider Tiles Layer).

### 2. Soumission (API Dispatch)
- Le client envoie un `POST /generate` à l'API (via Nginx).
- **FastAPI** (`backend/main.py`) reçoit la requête.
- Il **sérialise** la requête et l'envoie dans **Redis** via `celery.delay()`.
- Il retourne immédiatement un `task_id` au client.

### 3. Traitement (Worker)
- Le **Worker Celery** (`backend/tasks.py`) dépile la tâche.
- **Cache Check** : Il calcule un MD5 des paramètres et vérifie si le fichier existe déjà sur **MinIO (S3)**.
  - *Si oui* : Retourne l'URL S3 immédiatement.
- **Fetch** : Télécharge les données OSM (Routes, Eau, Parcs) en parallèle via `backend/fetcher.py`.
- **Render** : Génère le graphique Matplotlib via `backend/renderer.py` (Thread-safe).
- **Upload** : Le PNG/SVG/PDF final est uploadé sur le bucket S3 "posters".
- **Stateless** : Le worker ne stocke RIEN localement.

### 4. Polling & Résultat (Boucle)
- Le Frontend ( `src/lib/api.ts`) poll l'endpoint `/tasks/{id}` toutes les secondes.
- Quand le statut passe à `SUCCESS`, il récupère l'`file_url` (Lien S3 public).
- Le navigateur affiche l'image ou lance le téléchargement.

## 🏗️ Services Docker

| Service | Rôle | Port Interne | Port Public |
|---------|------|--------------|-------------|
| **nginx** | Gateway / Reverse Proxy | 80 | 80 |
| **api** | Dispatcher HTTP (FastAPI) | 8000 | - |
| **worker** | Exécution lourde (Celery) | - | - |
| **redis** | Broker de messages | 6379 | - |
| **minio** | Stockage Objet (S3) | 9000 | 9001 (Console) |
| **web** | Frontend (Node/Svelte) | 3000 | - |

## 🛡️ Sécurité & Performance

- **Rate Limiting** : 5 requêtes/minute/IP sur `/generate`.
- **Sentry** : Monitoring d'erreurs activé si `SENTRY_DSN` présent.
- **Cleanup** : Les objets S3 devraient avoir une Lifecycle Policy (ex: delete après 24h) configurée côté MinIO.
