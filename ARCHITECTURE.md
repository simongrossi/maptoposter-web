# Architecture Technique (v2.2)

Ce document decrit le fonctionnement interne de **MapPoster**, concu selon une
architecture microservices asynchrone et durcie pour un VPS mono-noeud.

## 🔄 Flux de donnees

### 1. Initialisation (Frontend)

- L'utilisateur configure son affiche dans SvelteKit.
- `SidebarControls.svelte` maintient l'etat (ville, theme, distance, DPI...).
- `MapSelector.svelte` met a jour la previsualisation Leaflet.
- Le navigateur recoit une session anonyme signee (`mp_session`) emise par
  l'API lors du premier appel `/api/*`.

### 2. Soumission (API Dispatch)

- Le client envoie `POST /api/generate` au gateway nginx.
- nginx retire le prefixe `/api` et transmet a FastAPI sur le reseau Docker.
- **FastAPI** (`backend/main.py`) :
  - valide la requete avec Pydantic (`backend/models.py`) ;
  - applique le quota journalier par IP, le plafond de taches actives par
    session et le plafond de file Redis ;
  - serialise la requete et l'envoie a **Redis** via `celery.apply_async()` ;
  - enregistre l'ownership `task_owner:<task_id> -> session` dans Redis ;
  - retourne immediatement `{"task_id": "..."}`.

### 3. Traitement (Worker)

- Le **worker Celery** (`backend/tasks.py`) depile la tache.
- **Cache S3** : il calcule un SHA-256 des parametres et verifie si l'objet
  existe deja dans le bucket prive.
  - *Si oui* : retourne la cle de l'objet (l'API signera l'URL).
- **Fetch** : telecharge les donnees OSM (routes, eau, parcs, couches custom)
  en parallele via `backend/fetcher.py`, avec cache disque.
- **Render** : genere le PNG/SVG/PDF via Matplotlib (`backend/renderer.py`).
- **Upload** : depose le fichier dans le bucket S3 prive via `backend/storage.py`.
- **Historique** : indexe la cle dans `session:<id>:objects` (liste bornee,
  expiree).
- **Stateless** : le worker ne conserve rien de durable en dehors du cache OSM
  et du stockage S3.

### 4. Polling et resultat

- Le frontend (`src/lib/api.ts`) poll `/api/tasks/{id}` avec backoff adaptatif.
- L'API verifie que la session courante est proprietaire de la tache.
- Quand le statut passe a `SUCCESS`, l'API signe une URL
  `/api/download/<cle>?expires=...&signature=...` et la renvoie dans
  `result.file_url`.
- Le navigateur charge l'image via nginx -> API. L'API streame l'objet depuis
  le stockage prive apres verification HMAC.
- **Geocoding** : la recherche avant passe par `/api/geocode` (proxy Nominatim
  borne et rate-limite).

## 🏗️ Services Docker

| Service | Role | Port interne | Port public |
|---|---|---|---|
| **gateway** (nginx) | Gateway / reverse proxy | 80 | `127.0.0.1:8080` |
| **web** | Frontend SvelteKit SSR | 3000 | - |
| **api** | Dispatcher FastAPI | 8000 | - |
| **worker** | Execution Celery/OSMnx/Matplotlib | - | - |
| **redis** | Broker + result backend | 6379 | - |
| **storage** | VersityGW S3 prive | 8333 | - |

### Reseaux

```text
edge (bridge)      : gateway, web, api, worker
data_net (internal): api, worker, redis, storage
```

- `data_net` est `internal: true` : Redis et le stockage n'ont pas de route
  sortante et ne sont pas joignables depuis `edge`.
- `edge` fournit la sortie Internet necessaire au worker (OSM) et a l'API
  (Nominatim).
- Seul le gateway publie un port, sur la boucle locale.

### Volumes

| Volume | Contenu | Utilise par |
|---|---|---|
| `redis_data` | AOF Redis | redis |
| `posters_data` | objets S3 (affiches) | storage |
| `osm_cache` | graphes/geometries OSM, cache de geocodage | worker |

## 🔐 Securite

- Redis : `requirepass`, pas de port publie, `maxmemory` + `noeviction`.
- Stockage : bucket prive, identifiants en variables d'environnement, aucun
  acces anonyme, aucun port publie.
- Posters : URLs HMAC signees et expirantes, streaming par l'API, jamais
  d'acces direct au stockage.
- Sessions : cookie anonyme signe, `HttpOnly`, `SameSite=Lax`, `Secure` derriere
  TLS.
- Enqueue : quota IP, plafond de taches actives, plafond de file, limite de
  taille de requete.
- Validation stricte : theme (anti-traversee), format, distance, dimensions,
  DPI, pixels, couches et couleurs.
- Worker : 2 Go de RAM maximum, concurrence 1, recyclage apres chaque tache,
  timeouts soft/hard.
- Conteneurs : images figees, utilisateurs non privilegies pour api/worker/web,
  `no-new-privileges`, `cap_drop`, logs avec rotation.
- Retention : nettoyage des posters anciens et plafonnement du nombre d'objets.

Voir [SECURITY.md](./SECURITY.md) pour le detail et les risques residuels.

## 🧹 Nettoyage

- Les objets S3 de plus de `POSTER_RETENTION_DAYS` jours (defaut 7) et au-dela
  de `MAX_STORED_POSTERS` (defaut 2000) sont supprimes au plus une fois par
  heure, protege par un verrou Redis.
- Les resultats Celery expirent apres `CELERY_RESULT_TTL` (defaut 1 h).
- Le cache OSM n'est pas nettoye automatiquement : surveiller la taille du
  volume `osm_cache` sur le long terme.
