# MapToPoster Web 🌍🎨

Une application web moderne pour transformer n'importe quel lieu du monde en une magnifique affiche minimaliste.

Basée sur les données **OpenStreetMap**, cette application permet de générer des posters haute résolution avec un style artistique épuré.

![Aperçu de l'application](static/preview.png)

## ✨ Fonctionnalités

- **Recherche Internationale** : Trouvez n'importe quelle ville ou village.
- **Aperçu WYSIWYG** : Sélectionnez votre zone avec une **fenêtre rectangulaire** simulant l'impression finale (format 3:4).
- **Styles Artistiques** : Choisissez parmi des thèmes prédéfinis (*Noir, Blueprint, Sunset, etc.*).
- **Personnalisation Complète** : Modifiez les couleurs (routes, eau, parcs, texte) pour créer votre propre style.
- **Micro-Services** : Architecture robuste séparant le **Frontend** (SvelteKit) du **Moteur de Rendu** (Python FastAPI).
- **Haute Résolution** : Exportez vos créations en PNG haute qualité pour l'impression.

---

## 🚀 Comment lancer le projet ?

Le projet utilise **Docker Compose** pour orchestrer l'ensemble de l'infrastructure. C'est la méthode recommandée.

### Prérequis

- [Docker](https://www.docker.com/products/docker-desktop/) installé sur votre machine.

### Démarrage rapide

1. **Cloner le projet**
   ```bash
   git clone https://github.com/votre-user/maptoposter-web.git
   cd maptoposter-web
   ```

2. **Lancer les services**
   Dans le dossier racine, exécutez :
   ```bash
   docker-compose up --build
   ```
   *La première fois, cela peut prendre quelques minutes pour construire les images et installer les dépendances Python (GeoPandas, Matplotlib, etc.).*

3. **Accéder à l'application**
   - Ouvrez votre navigateur sur : **[http://localhost:3000](http://localhost:3000)**

### Développement Local (Sans Docker)

Si vous préférez lancer les services séparément :

**1. Backend (Python)**
```bash
cd backend
# Créer un environnement virtuel (optionnel mais recommandé)
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r ../requirements.txt

# Lancer le serveur API
uvicorn main:app --reload --port 8000
```

**2. Frontend (Node.js)**
```bash
# Dans un nouveau terminal, à la racine
npm install
npm run dev
# L'app sera accessible sur http://localhost:5173
```
*Note : Assurez-vous que le frontend pointe vers la bonne URL API (via variables d'environnement).*

---

## 🛠️ Architecture Technique

Le projet est découpé en deux services principaux :

1.  **Backend (`/backend`)** :
    *   **FastAPI** : API REST performante.
    *   **OSMnx & GeoPandas** : Téléchargement et traitement des données géographiques.
    *   **AsyncIO** : Téléchargement parallèle des couches (Routes, Eau, Parcs).
    *   **Matplotlib (OO)** : Moteur de rendu graphique thread-safe.

2.  **Frontend (`/src`)** :
    *   **SvelteKit** : Framework fullstack pour une UI réactive.
    *   **Leaflet** : Carte interactive pour la sélection de zone.
    *   **Server-Side Events (SSE)** : Streaming de la progression en temps réel.

---

## 📜 Crédits & Licence

Ce projet est une évolution web moderne inspirée du script original [maptoposter Python](https://github.com/originalankur/maptoposter).

- **Données** : © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) (ODbL).
- **Core Library** : [OSMnx](https://github.com/gboeing/osmnx) par Geoff Boeing.
- **Licence** : Ce projet est sous licence **MIT**. Vous êtes libre de le modifier et de le redistribuer.
