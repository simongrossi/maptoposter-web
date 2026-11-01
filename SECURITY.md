# Securite de MapPoster Web

Ce document decrit le modele de menace, les mesures appliquees et les risques
residuels. Il correspond a la version `2.3.1` de la stack Docker.

## 1. Modele de menace

Hypotheses :

- Le VPS est mono-tenant. Un attaquant distant n'a acces qu'a `80/443` via
  Caddy, qui proxifie vers `127.0.0.1:8080` (gateway nginx).
- Les conteneurs, Docker et l'utilisateur `root` de l'hote sont consideres comme
  la frontiere de confiance. Une compromission de l'hote ou du socket Docker
  n'est pas couverte.
- L'application genere des images a partir de donnees OSM et de parametres
  fournis par des visiteurs anonymes. Le risque principal est l'abus de
  ressources (CPU/RAM/disque) et la fuite de localisations personnelles via les
  posters.
- Caddy termine le TLS. La configuration Caddy et le pare-feu de l'hote sont
  hors du depot ; la section 8 donne un exemple.

## 2. Surface d'attaque

| Element | Exposition | Justification |
|---|---|---|
| Caddy | `0.0.0.0:80`, `0.0.0.0:443` | unique entree publique, TLS |
| Gateway nginx | `127.0.0.1:8080` | accessible uniquement depuis l'hote (Caddy) |
| API FastAPI | reseau Docker `edge` | appelee par nginx, aucun port publie |
| Frontend SvelteKit | reseau Docker `edge` | appele par nginx, aucun port publie |
| Worker Celery | reseaux `edge` + `data_net` | sortie Internet pour OSM, aucun port |
| Redis | reseau Docker `data_net` (`internal: true`) | aucun port, aucun acces Internet |
| Stockage S3 (VersityGW) | reseau Docker `data_net` (`internal: true`) | aucun port, aucun acces Internet |

`data_net` est declare `internal: true` : Redis et le stockage n'ont aucune
route sortante et ne sont joignables que par l'API et le worker.

## 3. Mesures appliquees

### 3.1 Redis non expose et authentifie

- Aucun `ports:` : Redis n'est pas publie sur l'hote.
- `redis-server --requirepass "${REDIS_PASSWORD}"` : mot de passe obligatoire,
  fourni par `.env`, sans valeur par defaut dans le depot.
- `--maxmemory 192mb --maxmemory-policy noeviction` pour eviter une croissance
  non bornee et une perte silencieuse des taches en file.
- `appendonly yes` avec volume `redis_data`.
- Healthcheck `redis-cli ... ping`.
- `REDIS_PASSWORD` doit etre hexadecimal (`openssl rand -hex 32`) car il est
  insere dans une URL `redis://:motdepasse@redis:6379/0`.

### 3.2 Stockage objet prive, sans identifiants par defaut

`minio/minio` et `minio/mc` ne sont plus disponibles sur les registries
utilises. Le stockage est remplace par **VersityGW** (`versity/versitygw`,
backend POSIX), disponible sur Docker Hub et compatible S3 (SigV4, path-style).

- Image figee : `versity/versitygw:v1.10.0`.
- Identifiants racine uniquement via `S3_ACCESS_KEY` / `S3_SECRET_KEY` dans
  `.env` ; aucun ancien identifiant MinIO ni valeur de repli dans le code.
- Aucun port publie ; le service n'existe que sur `data_net`.
- Aucune policy anonyme, aucun bucket public, pas de console d'administration.
- Le bucket `S3_BUCKET` est cree au demarrage de l'API s'il n'existe pas.
- Les anciennes URLs `/minio_storage/...` renvoient `410 Gone`.

### 3.3 Posters servis par URL signee

- Le bucket est prive. Aucun objet n'est accessible directement.
- L'API signe une URL HMAC-SHA256 :
  `/api/download/<cle>?expires=<timestamp>&signature=<hex>`.
- Duree de vie par defaut : `DOWNLOAD_URL_TTL=900` (15 min). Les URLs de
  l'historique vivent 1 heure.
- La signature couvre la cle et l'expiration ; une cle modifiee ou une URL
  expiree renvoie `403`.
- La cle est validee par une allow-list de caracteres (pas de `..`, pas de
  separateur de chemin).
- Le fichier est streame par l'API depuis le stockage prive ; le stockage n'est
  jamais expose au navigateur.
- `Content-Security-Policy: default-src 'none'; sandbox` sur les SVG, pour
  empecher l'execution d'un script si un SVG est ouvert directement.
- Les signatures ne figurent pas dans les logs nginx : le format de log utilise
  `$uri` (sans query string) et non `$request`. Les cles `/api/download/...`
  (qui contiennent le slug de la ville) sont remplacees par
  `/api/download/[redacted]`.
- L'ancienne route `/posters/{filename}` et les PNG committes dans
  `static/posters/` ont ete supprimes : ils exposaient d'anciennes cartes
  (localisations personnelles) sans controle d'acces.

### 3.4 Enqueue protege

- **Session anonyme signee** : cookie `mp_session` `HttpOnly`, `SameSite=Lax`,
  `Secure` automatiquement si `X-Forwarded-Proto: https`, duree 7 jours. Le
  cookie contient un identifiant opaque et une signature HMAC ; il n'est pas
  un mecanisme d'authentification nominative mais une identite de session.
- **Quota par IP** : `GENERATE_RATE_LIMIT=5/minute` (SlowAPI) +
  `DAILY_GENERATE_QUOTA=50` par IP et par jour (compteur Redis).
- **Plafond de taches actives** : `MAX_ACTIVE_JOBS_PER_SESSION=2` par session,
  libere par le signal Celery `task_postrun` (avec expiration de securite).
- **Plafond de file** : `MAX_QUEUED_JOBS=20` (longueur de la liste Celery dans
  Redis). Au-dela : `503` avec `Retry-After`.
- **Taille de requete** : `client_max_body_size 64k` dans nginx et garde
  `Content-Length` cote FastAPI.
- **CSRF** : pas de CORS ouvert ; l'API n'accepte que du JSON same-origin. Un
  formulaire cross-site ne peut pas envoyer `application/json`, et
  `SameSite=Lax` ne joint pas le cookie sur un POST cross-site.
- **Ownership** : `/tasks/{id}`, `/download/{task_id}` et `/history` ne
  repondent que pour la session qui a cree la tache. Une tache d'autrui renvoie
  `404`, pas `403`, pour ne pas confirmer son existence.
- **Erreurs assainies** : les traces Python ne sont jamais renvoyees au client ;
  seuls des messages generiques sont exposes.

### 3.5 Validation stricte et plafonds de rendu

`backend/models.py` applique :

- `city` / `country` : 1 a 120 caracteres, pas de caracteres de controle.
- `style` : `^[a-z0-9_]{1,64}$` (empeche la traversee de repertoire
  `themes/../../...`).
- `format` : `png`, `svg` ou `pdf` uniquement.
- `distance` : 1 000 a 25 000 m (`MAX_DISTANCE_METERS`).
- `width` / `height` : 1 a 40 pouces.
- `dpi` : 72 a 600.
- `width * height * dpi^2 <= 100 000 000` pixels (`MAX_OUTPUT_PIXELS`), ce qui
  couvre A4/A3/12x16 a 600 DPI mais rejette les rendus demesures.
- `custom_layers` : 10 couches maximum, 8 tags par couche, cles/valeurs
  restreintes a un charset OSM sans syntaxe Overpass QL (pas de `"`, `]`, `;`,
  `(` ou `)`), pour eviter l'injection de requetes OSM.
- `custom_colors` : couleurs hexadecimale uniquement.
- `extra="forbid"` : tout champ inconnu produit une `422`.

Le texte des libelles est rendu avec `parse_math=False` : un `$` fourni par
l'utilisateur n'est pas interprete comme du mathtext Matplotlib.

### 3.6 Limites de ressources et resilience

| Service | `mem_limit` | `cpus` | `pids_limit` |
|---|---:|---:|---:|
| gateway | 128 Mo | 0.5 | 128 |
| redis | 256 Mo | 0.5 | 128 |
| storage | 256 Mo | 0.5 | 256 |
| api | 512 Mo | 1.0 | 256 |
| worker | 2 Go | 2.0 | 512 |
| web | 384 Mo | 1.0 | 256 |

- `memswap_limit` est egal a `mem_limit` : pas de debordement sur le swap.
- Le worker tourne avec `--concurrency=1`, `--max-tasks-per-child=1`,
  `--max-memory-per-child=1500000` et `-Ofair`. Une tache lourde ne peut pas
  s'executer en parallele d'une autre.
- `task_soft_time_limit` / `task_time_limit` : 480 s / 540 s par defaut.
- Le worker est recycle apres chaque tache (processus enfant), ce qui libere
  les fuites memoire de Matplotlib/OSMnx. Si une zone tres dense depasse malgre
  tout les 2 Go, le cgroup tue le processus (OOM) : la tache echoue, le worker
  redemarre et le compteur de tache active expire apres `ACTIVE_JOB_TTL`.
- Le telechargement OSM n'est plus sur-dimensionne par le ratio de l'affiche :
  le renderer recadre dans un carre de rayon `distance`, donc le worker ne
  telecharge que la zone utile.
- `restart: unless-stopped` sur tous les services.
- Healthchecks : `redis` (`PING`), `storage` (`/_/health`), `api`
  (`/health`), `web` (`/`), `gateway` (`/healthz`).
- Logs Docker en `json-file` avec rotation `10m x 3`.
- Retention : `POSTER_RETENTION_DAYS=7` et `MAX_STORED_POSTERS=2000`, nettoyage
  opportuniste au plus une fois par heure (verrou Redis).

### 3.7 Images et conteneurs

Images figees :

| Service | Image |
|---|---|
| gateway | `nginx:1.28.0-alpine` |
| redis | `redis:7.4.2-alpine` |
| storage | `versity/versitygw:v1.10.0` |
| api / worker | build local depuis `python:3.11.11-slim-bookworm` |
| web | build local depuis `node:22.14.0-alpine3.21` |

- API, worker et frontend tournent avec un utilisateur non privilegie
  (`app` UID 10001, `node`).
- `no-new-privileges:true` sur tous les services.
- `cap_drop: [ALL]` sur `api`, `worker` et `web` (aucun privilege Linux requis).
- Aucun montage du socket Docker, aucun mode `privileged`, aucun port autre que
  `127.0.0.1:8080`.
- `.dockerignore` exclut `.env`, `.git`, `node_modules`, tests et caches du
  contexte de build.
- Documentation OpenAPI desactivee par defaut (`ENABLE_DOCS=false`).
- CORS ouvert supprime.
- `Permissions-Policy: geolocation=(self)` pour autoriser uniquement le bouton
  « Ma position » sur notre origine ; camera et microphone restent bloques.
- Sentry : `send_default_pii=False`, `max_request_body_size="never"`, traces
  echantillonnees a 10 % par defaut, profilage desactive.

## 4. Gestion des secrets

Les secrets obligatoires sont :

| Variable | Usage |
|---|---|
| `REDIS_PASSWORD` | mot de passe Redis |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | identifiants S3 (root VersityGW) |
| `SESSION_SECRET` | signature des cookies de session |
| `DOWNLOAD_SIGNING_SECRET` | signature des URLs de telechargement |

Regles :

- Aucune valeur par defaut dans le code ou dans Compose. `docker compose`
  refuse de demarrer si une variable obligatoire est vide (`:?`).
- `./scripts/init-env.sh` cree `.env` en mode `600` et genere des valeurs
  aleatoires avec `openssl`.
- `.env` est ignore par git et exclu du contexte Docker.
- Ne jamais reutiliser les anciens identifiants MinIO.
- Rotation : modifier les variables puis `docker compose up -d --force-recreate`.
  Changer `SESSION_SECRET` invalide toutes les sessions ; changer
  `DOWNLOAD_SIGNING_SECRET` invalide toutes les URLs signees en circulation.

## 5. Risques residuels

Ces risques sont acceptes ou necessitent une action d'exploitation.

1. **Pas de comptes utilisateurs.** La session est anonyme : vider ses cookies
   perd l'historique, et un attaquant peut obtenir autant de sessions qu'il
   veut. Les quotas par IP restent contournables avec un botnet ou un pool de
   proxys. Une protection CAPTCHA / WAF n'est pas en place.
2. **Quota par IP dependant de Caddy.** nginx fait confiance a
   `X-Forwarded-For` provenant des plages privees/loopback. Si le port `8080`
   etait expose autrement que sur `127.0.0.1`, un client pourrait usurper son
   IP. Le bind loopback et le pare-feu de l'hote sont donc critiques.
3. **Identifiants S3 racine.** VersityGW n'a qu'un compte root ; une
   compromission de l'API ou du worker donne un acces complet au stockage.
   Il n'y a pas d'IAM par bucket.
4. **Secrets en variables d'environnement.** Toute personne ayant acces a
   `docker inspect` ou au socket Docker peut les lire. Docker Swarm secrets,
   Vault ou SOPS ne sont pas utilises.
5. **Chiffrement au repos absent.** Les posters et le cache OSM sont en clair
   sur le volume du VPS. Les posters peuvent reveler une localisation
   personnelle. La retention limite la fenetre d'exposition mais ne garantit
   pas un effacement physique (snapshots, backups, blocs SSD).
6. **Redis non chiffre en transit.** Le trafic Redis circule en clair dans le
   reseau Docker `data_net`. L'isolation reseau est la contre-mesure.
7. **Images figees par tag, pas par digest.** Une republication malveillante
   du tag resterait possible. Pour un niveau superieur, epingler les digests
   `@sha256:...` et activer un miroir de registre.
8. **Dependances Python non verrouillees.** `requirements.txt` ne contient pas
   de versions ni de hashes. Une attaque supply-chain sur PyPI reste possible.
   Recommandation : `pip-compile` + `--require-hashes`.
9. **Compromission de l'hote hors perimetre.** Un acces root au VPS permet de
   lire les volumes, les secrets et les logs.
10. **Deni de service applicatif.** Les plafonds limitent l'impact, mais
    plusieurs IP peuvent encore saturer la file ou le CPU dans les limites
    autorisees. Un reverse proxy avec limitation globale (Caddy + CrowdSec,
    fail2ban) est recommande.
11. **Nominatim / OSM.** Le proxy `/geocode` est limite a 10 requetes/minute,
    mais le worker peut etre bloque par Nominatim/Overpass en cas d'usage
    intensif. Les tuiles de previsualisation sont servies par
    `tile.openstreetmap.org` (sans cle API) : en cas de trafic important,
    auto-heberger les tuiles ou utiliser un fournisseur dedie. Respecter les
    conditions d'utilisation et prevoir un fournisseur de geocodage
    auto-heberge si necessaire.
12. **Cache pickle local.** Le cache OSM utilise `pickle` dans un volume
    accessible au worker. Une compromission du worker permet de manipuler ce
    cache ; il n'est jamais expose au client.
13. **Pas de `read_only` rootfs.** Les conteneurs API/worker/frontend ne sont
    pas en systeme de fichiers racine en lecture seule, pour rester compatibles
    avec Matplotlib/OSMnx. `no-new-privileges` et `cap_drop` reduisent l'impact.
14. **Pas de sauvegarde automatique.** Les volumes `posters_data`,
    `redis_data` et `osm_cache` ne sont pas sauvegardes. Une perte de volume
    supprime l'historique et la file.
15. **Pas de journal d'audit applicatif.** Les logs nginx/Docker sont les seuls
    journaux. Ils excluent les query strings (donc les signatures) mais
    contiennent les IP clientes et les chemins. Si les logs d'acces Caddy sont
    actives, ils peuvent contenir les query strings des URLs signees : les
    filtrer ou les desactiver.
16. **Sentry.** Le DSN est optionnel et les evenements sont nettoyes de leurs
    query strings, mais un DSN compromis reste un canal de fuite des traces
    applicatives. Ne l'activer que si necessaire.
17. **Rate limiting en memoire.** SlowAPI utilise un stockage local au
    processus. La stack lance une seule instance API ; si elle est scalee, il
    faut configurer un stockage Redis pour que les limites soient globales.
18. **Geolocalisation.** Le bouton « Ma position » est strictement opt-in et
    declenche la demande d'autorisation du navigateur. Les coordonnees sont
    envoyees directement a Nominatim pour le reverse geocoding via HTTPS ; elles
    ne sont ni stockees par MapPoster ni incluses dans les posters sans action
    de l'utilisateur. Un refus de permission laisse la carte inchangee.

## 6. Verification apres deploiement

Depuis le VPS :

```bash
# 1. Seuls les ports attendus ecoutent
sudo ss -ltnp | grep -E ':(80|443|8080|6379|9000|9001)\b'
# Attendu : 80/443 (Caddy), 8080 sur 127.0.0.1 uniquement.
# Aucun 6379, 9000, 9001.

# 2. La pile est saine
docker compose ps
docker compose logs --tail=50 api worker storage redis gateway

# 3. Redis et le stockage ne sont pas joignables depuis l'hote
nc -zv 127.0.0.1 6379   # doit echouer
nc -zv 127.0.0.1 9000   # doit echouer

# 4. L'API repond uniquement via le gateway
curl -sS http://127.0.0.1:8080/api/health
curl -sS http://127.0.0.1:8080/api/ready

# 5. Une URL non signee est refusee
curl -sS -o /dev/null -w '%{http_code}\n' \
  'http://127.0.0.1:8080/api/download/paris_noir_0123456789ab.png'
# Attendu : 403

# 6. Une signature invalide est refusee
curl -sS -o /dev/null -w '%{http_code}\n' \
  'http://127.0.0.1:8080/api/download/paris_noir_0123456789ab.png?expires=4000000000&signature=0000000000000000000000000000000000000000000000000000000000000000'
# Attendu : 403

# 7. Memoire du worker plafonnee
docker stats --no-stream "$(docker compose ps -q worker)"
# La colonne MEM USAGE / LIMIT doit afficher ... / 2GiB.

# 8. Aucun identifiant par defaut dans le depot
grep -RIn --exclude-dir=.git --exclude-dir=node_modules \
  -E 'MINIO_ROOT_(USER|PASSWORD)' . || true
```

## 7. Reponse a incident

1. **Fuite de secret** : regenerer la variable concernee dans `.env`, puis
   `docker compose up -d --force-recreate`. Pour `S3_ACCESS_KEY`/`S3_SECRET_KEY`,
   recreer le conteneur de stockage et verifier l'acces aux objets.
2. **URL signee divulguee** : changer `DOWNLOAD_SIGNING_SECRET` invalide
   immediatement toutes les URLs. Les posters restent dans le bucket prive.
3. **Poster sensible** : supprimer l'objet via l'API S3 interne (ou purger le
   volume `posters_data` apres arret de la stack), puis tourner les secrets.
4. **Abus** : bloquer l'IP dans Caddy ou au pare-feu ; reduire
   `DAILY_GENERATE_QUOTA` / `MAX_QUEUED_JOBS` ; redemarrer le worker.
5. **Compromission de l'hote** : considerer tous les secrets comme compromis,
   reconstruire le VPS, restaurer les volumes depuis une sauvegarde saine.

## 8. Exemple Caddy (hote)

```caddyfile
posters.example.com {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8080
}
```

Caddy occupe `80/443`, gere le certificat et l'HSTS. nginx ne voit que du HTTP
sur `127.0.0.1:8080`. Ne pas publier `8080` sur `0.0.0.0`.
