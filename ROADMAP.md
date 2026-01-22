# Roadmap Technique & Améliorations Futures

Ce document recense les axes d'amélioration identifiés pour passer du prototype actuel à une application de production robuste, performante et sécurisée.

## 1. Architecture et Performances (Backend)

### 🔴 Critique : File d'attente (Task Queue)
**Problème** : Le lancement direct de processus Python via `spawn` pour chaque requête est non-scalable et risque de saturer le serveur (CPU/RAM).
**Solution** : 
- Implémenter une **file de tâches** (ex: BullMQ avec Redis).
- Le serveur web ajoute la requête à la file.
- Un ou plusieurs **workers** Python dépilent et traitent les générations séquentiellement.

### ✅ Important : Service Python Persistant
**Solution** : 
- Création d'une API **FastAPI** (`backend/main.py`) tournant en continu.
- Bibliothèques chargées au démarrage (plus de cold start).

### ✅ Optimisation : Parallélisation
**Solution** : Utilisation de `asyncio` et `ThreadPoolExecutor` dans `backend/fetcher.py` pour paralléliser les téléchargements OSM.

## 2. Code Python (`backend/`)

### ✅ Robustesse : Gestion du Cache
**Amélioration** : Implémenté dans `backend/cache.py` avec hachage **MD5** des clés.

### ✅ Performance : Matplotlib
**Amélioration** : Utilisation de l'approche Orientée Objet `Figure` dans `backend/renderer.py`.

### ✅ Qualité : Refactoring
**Amélioration** : Code découpé en modules : `main`, `fetcher`, `renderer`, `models`, `utils`.

## 3. Frontend et UX (SvelteKit)

### ✅ Critique : Prévisualisation Réaliste
**Solution** : Implémenté dans `MapSelector.svelte` avec `L.rectangle` respectant le ratio 3:4.

### ✅ Qualité : Typage TypeScript
**Amélioration** : Utilisation des types `@types/leaflet`.

### ✅ Fonctionnalité : Personnalisation Avancée
**Réalisé** : 
- Sélecteur de couleurs personnalisées (Fond, Eau, Parcs, Routes, Texte) ajouté à l'UI.

## 4. DevOps et Sécurité

### ✅ Optimisation : Docker
**Amélioration** : 
- **Multi-stage build** implémenté pour `backend` et `frontend`.
- `docker-compose.yml` orchestrant les services.

### ✅ Important : Persistance
**Solution** : Volumes Docker configurés pour le cache et les fichiers statiques.
