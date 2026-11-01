# Frontend Documentation 🎨

Application **SvelteKit** moderne utilisant TypeScript.

## 📂 Structure

- **`routes/+page.svelte`** : Le Chef d'Orchestre.
    - Il ne contient PAS de logique métier complexe (juste le State Management global).
    - Il importe et coordonne les composants "intelligents".
- **`lib/components/`** :
    - `SidebarControls.svelte` : Le formulaire géant (Inputs, Sliders, Color Pickers). Gère la validation UI.
    - `MapSelector.svelte` : Carte Leaflet interactive. Gère le Geocoding (Nominatim), la sélection de zone (Rectangle) et la prévisualisation des tuiles (Dark/Light).
    - `PosterPreview.svelte` : Liste des affiches générées.
    - `GenerationProgress.svelte` : Barre de progression.
- **`lib/api.ts`** :
    - Abstraction de `fetch`. Contient la logique de **Polling** (`pollTaskStatus`) qui transforme l'API asynchrone en Promise résolue.

## 📱 Mobile & Responsive

Le layout réagit aux breakpoints (`max-width: 768px`).
- **Desktop** : Sidebar fixe à gauche (380px), Carte à droite (flex 1).
- **Mobile** : Carte plein écran. Sidebar transformée en "Drawer" (Off-canvas) qui glisse via CSS transform.
  - État géré par `mobileMenuOpen` dans `+page.svelte`.

## 🌍 Map Tiles Logic

Le composant `MapSelector` utilise une seule source de tuiles, **OSM Standard**
(`https://tile.openstreetmap.org/{z}/{x}/{y}.png`), sans clé API. Le rendu
sombre ou clair est obtenu par un filtre CSS appliqué uniquement au calque des
tuiles, pas au marqueur ni au rectangle de sélection.
- Thème `noir` / sombre -> OSM + filtre `grayscale + invert`.
- Thème `minimal` / clair -> OSM + filtre `grayscale`.
- Thème `standard` -> OSM sans filtre.

Attention à la [politique d'utilisation des tuiles OSM](https://operations.osmfoundation.org/policies/tiles/) :
pour un trafic important, auto-héberger les tuiles ou utiliser un fournisseur
dédié.
