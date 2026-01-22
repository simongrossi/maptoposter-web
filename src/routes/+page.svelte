<script lang="ts">
    import { onMount, tick } from "svelte";
    import MapSelector from "$lib/components/MapSelector.svelte";
    import type {
        Theme,
        GenerationRequest,
        GenerationResponse,
        CustomLayer,
    } from "$lib/types";
    import { fetchThemes, generatePoster } from "$lib/api";

    // Interfaces
    interface MapComponent {
        flyToLocation: (query: string) => void;
    }

    // State
    let city = "Paris";
    let country = "France";
    let name = "";
    let countryLabel = "";

    let distance = 10000;

    // Export State
    let exportFormat = "png";

    // Options
    let allThemes = false;
    let selectedTheme = "";
    let themes: Theme[] = [];

    let customLayers: CustomLayer[] = [
        {
            label: "Pistes Cyclables",
            tags: { highway: "cycleway" },
            color: "#3498db",
            enabled: false,
            width: 1.0,
        },
        {
            label: "Voies Ferrées",
            tags: { railway: "rail" },
            color: "#f1c40f",
            enabled: false,
            width: 1.2,
        },
        {
            label: "Métro",
            tags: { railway: "subway" },
            color: "#e74c3c",
            enabled: false,
            width: 1.5,
        },
        {
            label: "Forêts & Nature",
            tags: {
                natural: ["wood", "scrub", "tree_row"],
                landuse: ["forest", "orchard"],
            },
            color: "#27ae60",
            enabled: false,
            width: 0.5, // Filled polygons don't really use width but good for boundaries
        },
        {
            label: "Fleuves & Rivières",
            tags: { waterway: ["river", "stream", "canal"] },
            color: "#2980b9",
            enabled: false,
            width: 1.5,
        },
    ];

    // App State
    let loading = false;
    let generatedFiles: string[] = [];
    let errorMsg = "";
    let debugInfo = "";
    let mapComponent: MapComponent;

    // Custom Colors State
    let customColorsEnabled = false;
    let customColors = {
        bg: "#ffffff",
        water: "#a6cee3",
        parks: "#b2df8a",
        roads: "#555555",
        text: "#333333",
    };

    // Progress State
    let progressPercent = 0;
    let progressText = "";
    let abortController: AbortController | null = null;

    // Debounce for forward geocoding
    let searchTimeout: ReturnType<typeof setTimeout>;

    onMount(async () => {
        themes = await fetchThemes();
        if (themes.length > 0) {
            // Default to 'noir' or first one
            const defaultTheme =
                themes.find((t) => t.id === "noir") || themes[0];
            if (defaultTheme) selectedTheme = defaultTheme.id;
        }
    });

    // Reactivity for map updates (Forward Geocoding)
    function handleInputChange() {
        if (searchTimeout) clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            if (city && country && mapComponent) {
                mapComponent.flyToLocation(`${city}, ${country}`);
            }
        }, 1200);
    }

    // Handle map updates (Reverse Geocoding)
    function handleLocationSelect(event: CustomEvent) {
        // Only update if different to avoid loops/jitter
        // Ideally we trust the map's reverse geocoding as "truth" when the user drags
        const { city: c, country: co } = event.detail;

        // Update without triggering the forward debounce if possible,
        // but for now simple assignment is fine as long as defaults match.
        if (c && c !== city) city = c;
        if (co && co !== country) country = co;
    }

    function triggerSearch() {
        if (searchTimeout) clearTimeout(searchTimeout);
        if (city && country && mapComponent) {
            mapComponent.flyToLocation(`${city}, ${country}`);
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Enter") {
            event.preventDefault();
            triggerSearch();
        }
    }

    function cancelGeneration() {
        if (abortController) {
            abortController.abort();
            abortController = null;
            loading = false;
            progressText = "Annulé par l'utilisateur";
        }
    }

    async function handleSubmit() {
        if (!city || !country) return;

        loading = true;
        errorMsg = "";
        debugInfo = "";
        generatedFiles = [];
        progressPercent = 0;
        progressText = "Démarrage...";

        abortController = new AbortController();

        const payload: GenerationRequest = {
            city,
            country,
            name: name || undefined,
            countryLabel: countryLabel || undefined,
            distance,
            theme: !allThemes ? selectedTheme : undefined,
            allThemes: allThemes,
            customLayers: customLayers, // Send custom layers
            customColors: customColorsEnabled ? customColors : undefined,
            format: exportFormat,
        };

        const result = await generatePoster(
            payload,
            (percent, text) => {
                progressPercent = percent;
                progressText = text;
            },
            abortController.signal,
        );

        if (result.success) {
            generatedFiles = result.files;
        } else {
            errorMsg = result.error || "Une erreur est survenue.";
            if (result.debug) debugInfo = result.debug;
        }

        loading = false;
        abortController = null;
    }
</script>

<div class="app-container">
    <aside class="sidebar">
        <header>
            <div class="logo">Map<span class="highlight">Poster</span></div>
            <p class="subtitle">Créez des affiches artistiques de villes</p>
        </header>

        <form on:submit|preventDefault={handleSubmit} class="controls">
            <!-- Location Section -->
            <div class="section">
                <h3><span class="icon">📍</span> Localisation</h3>
                <div class="form-group">
                    <label for="city">Ville</label>
                    <input
                        id="city"
                        type="text"
                        bind:value={city}
                        on:input={handleInputChange}
                        on:keydown={handleKeydown}
                        required
                        placeholder="Paris"
                    />
                </div>
                <div class="form-group">
                    <label for="country">Pays</label>
                    <input
                        id="country"
                        type="text"
                        bind:value={country}
                        on:input={handleInputChange}
                        on:keydown={handleKeydown}
                        required
                        placeholder="France"
                    />
                </div>
                <button
                    type="button"
                    class="btn-search"
                    on:click={triggerSearch}
                >
                    🔍 Aperçu
                </button>
            </div>

            <!-- Style Section -->
            <div class="section">
                <h3><span class="icon">🎨</span> Style & Thème</h3>

                <div class="form-group checkbox-group">
                    <label class="toggle">
                        <input type="checkbox" bind:checked={allThemes} />
                        <span class="slider"></span>
                        <span class="label-text">Générer tous les thèmes</span>
                    </label>
                </div>

                {#if !allThemes}
                    <div class="form-group">
                        <label for="theme">Thème</label>
                        <select
                            id="theme"
                            bind:value={selectedTheme}
                            disabled={themes.length === 0}
                        >
                            {#each themes as t}
                                <option value={t.id}>
                                    {t.name}
                                </option>
                            {/each}
                        </select>
                    </div>
                {/if}
            </div>

            <!-- Custom Colors Section -->
            <div class="section">
                <h3><span class="icon">🎨</span> Couleurs Perso.</h3>

                <div class="form-group checkbox-group">
                    <label class="toggle">
                        <input
                            type="checkbox"
                            bind:checked={customColorsEnabled}
                        />
                        <span class="slider"></span>
                        <span class="label-text"
                            >Activer couleurs personnalisées</span
                        >
                    </label>
                </div>

                {#if customColorsEnabled}
                    <div class="color-grid">
                        <div class="color-item">
                            <label>Fond</label>
                            <input type="color" bind:value={customColors.bg} />
                        </div>
                        <div class="color-item">
                            <label>Eau</label>
                            <input
                                type="color"
                                bind:value={customColors.water}
                            />
                        </div>
                        <div class="color-item">
                            <label>Parcs</label>
                            <input
                                type="color"
                                bind:value={customColors.parks}
                            />
                        </div>
                        <div class="color-item">
                            <label>Routes</label>
                            <input
                                type="color"
                                bind:value={customColors.roads}
                            />
                        </div>
                        <div class="color-item">
                            <label>Texte</label>
                            <input
                                type="color"
                                bind:value={customColors.text}
                            />
                        </div>
                    </div>
                {/if}
            </div>

            <!-- Additional Layers Section -->
            <div class="section">
                <h3><span class="icon">🛤️</span> Couches Sup.</h3>

                {#each customLayers as layer}
                    <div class="layer-control">
                        <div class="form-group checkbox-group">
                            <label class="toggle">
                                <input
                                    type="checkbox"
                                    bind:checked={layer.enabled}
                                />
                                <span class="slider"></span>
                                <span class="label-text">{layer.label}</span>
                            </label>
                        </div>
                        {#if layer.enabled}
                            <div class="layer-settings">
                                <input
                                    type="color"
                                    bind:value={layer.color}
                                    class="color-picker"
                                    title="Couleur"
                                />
                                <div
                                    class="width-control"
                                    title="Taille / Épaisseur du trait"
                                >
                                    <input
                                        type="range"
                                        min="0.5"
                                        max="5"
                                        step="0.5"
                                        bind:value={layer.width}
                                    />
                                    <span class="value">{layer.width}</span>
                                </div>
                            </div>
                        {/if}
                    </div>
                {/each}
            </div>

            <!-- Export Options -->
            <div class="section">
                <h3><span class="icon">💾</span> Export</h3>
                <div class="form-group">
                    <label>Format de fichier</label>
                    <div class="format-idx">
                        {#each ["png", "svg", "pdf"] as f}
                            <label
                                class="radio-card {exportFormat === f
                                    ? 'active'
                                    : ''}"
                            >
                                <input
                                    type="radio"
                                    bind:group={exportFormat}
                                    value={f}
                                />
                                {f.toUpperCase()}
                            </label>
                        {/each}
                    </div>
                </div>
            </div>

            <!-- Customization Section -->
            <div class="section">
                <h3><span class="icon">✏️</span> Personnalisation</h3>
                <div class="grid-2">
                    <div class="form-group">
                        <label for="name">Titre</label>
                        <input
                            id="name"
                            type="text"
                            bind:value={name}
                            placeholder={city}
                        />
                    </div>
                    <div class="form-group">
                        <label for="cLabel">Sous-titre</label>
                        <input
                            id="cLabel"
                            type="text"
                            bind:value={countryLabel}
                            placeholder={country}
                        />
                    </div>
                </div>

                <div class="form-group">
                    <label for="distance">
                        Rayon: {(distance / 1000).toFixed(1)} km
                        <span class="hint">
                            {#if distance < 6000}
                                (Centre)
                            {:else if distance < 15000}
                                (Ville)
                            {:else}
                                (Métropole)
                            {/if}
                        </span>
                    </label>
                    <input
                        id="distance"
                        type="range"
                        bind:value={distance}
                        min="2000"
                        max="50000"
                        step="1000"
                    />
                </div>
            </div>

            {#if loading}
                <div class="progress-container">
                    <div class="progress-info">
                        <span class="progress-text">{progressText}</span>
                        <span class="progress-percent">{progressPercent}%</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div
                            class="progress-bar-fill"
                            style="width: {progressPercent}%"
                        ></div>
                    </div>
                    <button
                        type="button"
                        class="btn-cancel"
                        on:click={cancelGeneration}
                    >
                        ⛔ Arrêter
                    </button>
                </div>
            {:else}
                <button type="submit" class="btn-generate">
                    ✨ Générer l'affiche
                </button>
            {/if}

            {#if errorMsg}
                <div class="error-banner">
                    {errorMsg}
                </div>
            {/if}
        </form>

        {#if generatedFiles.length > 0}
            <div class="results-list">
                <h4>Affiches récentes</h4>
                <div class="posters-scroll">
                    {#each generatedFiles as file}
                        <div class="mini-card">
                            <span class="filename" title={file}>{file}</span>
                            <div class="actions">
                                <a href="/posters/{file}" target="_blank">👁️</a>
                                <a href="/posters/{file}" download>⬇️</a>
                            </div>
                        </div>
                    {/each}
                </div>
            </div>
        {/if}

        <footer class="sidebar-footer">
            <a href="/about">
                <span class="icon">ℹ️</span> À propos & Crédits
            </a>
        </footer>
    </aside>

    <main class="map-area">
        <MapSelector
            bind:this={mapComponent}
            {distance}
            on:locationSelect={handleLocationSelect}
        />
        <div class="map-overlay">
            <div class="info-badge">Aperçu de la zone de couverture</div>
        </div>
    </main>
</div>

<style>
    :global(body) {
        margin: 0;
        font-family:
            "Inter",
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            sans-serif;
        background: #1a1b1e;
        color: #e0e0e0;
        height: 100vh;
        overflow: hidden;
    }

    .app-container {
        display: flex;
        height: 100vh;
        width: 100vw;
    }

    /* Sidebar Styles */
    .sidebar {
        width: 380px;
        background: #25262b;
        border-right: 1px solid #2c2e33;
        display: flex;
        flex-direction: column;
        z-index: 10;
        box-shadow: 4px 0 20px rgba(0, 0, 0, 0.2);
        overflow-y: auto;
    }

    header {
        padding: 24px;
        border-bottom: 1px solid #2c2e33;
        background: #25262b;
    }

    .logo {
        font-size: 1.5rem;
        font-weight: 800;
        color: white;
        letter-spacing: -0.5px;
    }

    .highlight {
        color: #4dabf7;
    }

    .subtitle {
        color: #909296;
        font-size: 0.85rem;
        margin: 4px 0 0 0;
    }

    .controls {
        padding: 24px;
        flex: 1;
    }

    .section {
        margin-bottom: 28px;
    }

    h3 {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #909296;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .icon {
        font-size: 1.1rem;
    }

    .form-group {
        margin-bottom: 16px;
    }

    label {
        display: block;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 6px;
        color: #c1c2c5;
    }

    input[type="text"],
    select {
        width: 100%;
        padding: 10px 12px;
        background: #2c2e33;
        border: 1px solid #373a40;
        border-radius: 6px;
        color: white;
        font-size: 0.95rem;
        transition: all 0.2s;
        box-sizing: border-box; /* Fix padding expanding width */
    }

    input[type="text"]:focus,
    select:focus {
        outline: none;
        border-color: #4dabf7;
        box-shadow: 0 0 0 2px rgba(77, 171, 247, 0.2);
    }

    .grid-2 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }

    /* Range Slider */
    input[type="range"] {
        width: 100%;
        height: 6px;
        background: #373a40;
        border-radius: 3px;
        outline: none;
        -webkit-appearance: none;
        appearance: none;
    }

    input[type="range"]::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 18px;
        height: 18px;
        background: #4dabf7;
        border-radius: 50%;
        cursor: pointer;
        transition: transform 0.1s;
    }

    input[type="range"]::-webkit-slider-thumb:hover {
        transform: scale(1.1);
    }

    .hint {
        font-size: 0.75rem;
        color: #909296;
        font-weight: normal;
        margin-left: 6px;
    }

    /* Toggle Switch */
    .toggle {
        position: relative;
        display: inline-flex;
        align-items: center;
        cursor: pointer;
    }

    .toggle input {
        opacity: 0;
        width: 0;
        height: 0;
    }

    .slider {
        position: relative;
        width: 40px;
        height: 22px;
        background-color: #373a40;
        border-radius: 22px;
        transition: 0.4s;
        margin-right: 12px;
    }

    .slider:before {
        position: absolute;
        content: "";
        height: 16px;
        width: 16px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        border-radius: 50%;
        transition: 0.4s;
    }

    input:checked + .slider {
        background-color: #4dabf7;
    }

    input:checked + .slider:before {
        transform: translateX(18px);
    }

    .label-text {
        font-size: 0.9rem;
    }

    /* Generate Button */
    .btn-generate {
        width: 100%;
        padding: 14px;
        background: linear-gradient(135deg, #4dabf7 0%, #339af0 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition:
            transform 0.1s,
            box-shadow 0.2s;
        box-shadow: 0 4px 12px rgba(51, 154, 240, 0.3);
    }

    .btn-generate:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(51, 154, 240, 0.4);
    }

    .btn-generate:active:not(:disabled) {
        transform: translateY(0);
    }

    .btn-generate:disabled {
        background: #373a40;
        color: #909296;
        cursor: wait;
        box-shadow: none;
    }

    /* Results */
    .results-list {
        padding: 0 24px 24px 24px;
        border-top: 1px solid #2c2e33;
    }

    .posters-scroll {
        max-height: 200px;
        overflow-y: auto;
    }

    .mini-card {
        background: #2c2e33;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .filename {
        font-size: 0.8rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 200px;
    }

    .actions a {
        text-decoration: none;
        margin-left: 8px;
        font-size: 1.1rem;
        color: #909296;
        transition: color 0.2s;
    }

    .actions a:hover {
        color: white;
    }

    .error-banner {
        margin-top: 16px;
        padding: 12px;
        background: #fa5252;
        color: white;
        border-radius: 6px;
        font-size: 0.9rem;
    }

    /* Map Area */
    .map-area {
        flex: 1;
        position: relative;
        background: #1a1b1e;
    }

    .map-overlay {
        position: absolute;
        top: 20px;
        right: 20px;
        z-index: 500; /* Leaflet is around 400 */
        pointer-events: none;
    }

    .btn-search {
        width: 100%;
        padding: 8px;
        background: #373a40;
        color: #c1c2c5;
        border: 1px solid #484b51;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.9rem;
        transition: all 0.2s;
        margin-top: 4px;
    }

    .btn-search:hover {
        background: #484b51;
        color: white;
        border-color: #5c5f66;
    }

    .info-badge {
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(4px);
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.1);
        pointer-events: auto; /* Block clicks falling through to map */
        cursor: default;
    }

    .sidebar-footer {
        padding: 24px;
        border-top: 1px solid #2c2e33;
        margin-top: auto;
    }

    .sidebar-footer a {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #909296;
        text-decoration: none;
        font-size: 0.85rem;
        transition: color 0.2s;
    }

    .sidebar-footer a:hover {
        color: #4dabf7;
    }

    /* Progress Bar Styles */
    .progress-container {
        width: 100%;
        margin-top: 10px;
    }

    .progress-info {
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        color: #c1c2c5;
        margin-bottom: 6px;
    }

    .progress-bar-bg {
        width: 100%;
        height: 8px;
        background: #373a40;
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 12px;
    }

    .progress-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #4dabf7, #3bc9db);
        transition: width 0.3s ease-out;
    }

    .btn-cancel {
        width: 100%;
        padding: 10px;
        background: #fa5252;
        color: white;
        border: none;
        border-radius: 6px;
        font-size: 0.9rem;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.2s;
    }

    .btn-cancel:hover {
        background: #e03131;
    }

    .color-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-top: 10px;
    }

    .color-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 100%; /* Ensure flex items take space */
    }

    .color-item label {
        font-size: 0.75rem;
        margin-bottom: 4px;
        color: #adb5bd;
    }

    .color-item input[type="color"] {
        width: 100%;
        height: 32px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        padding: 0;
        background: none;
    }

    /* Layer Controls */
    .layer-control {
        margin-bottom: 12px;
    }

    .layer-settings {
        display: flex;
        gap: 12px;
        align-items: center;
        margin-top: 8px;
        margin-left: 52px; /* Align with text */
        background: #25262b;
        padding: 8px;
        border-radius: 6px;
    }

    .layer-settings .color-picker {
        width: 32px;
        height: 32px;
        border: none;
        padding: 0;
        background: none;
        cursor: pointer;
    }

    .width-control {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;
    }

    .width-control input[type="range"] {
        flex: 1;
        height: 4px;
    }

    .width-control .value {
        font-size: 0.75rem;
        color: #909296;
        min-width: 24px;
        text-align: right;
    }

    /* Format Selector */
    .format-idx {
        display: flex;
        gap: 8px;
        margin-top: 8px;
    }

    .radio-card {
        flex: 1;
        text-align: center;
        padding: 10px;
        background: #373a40;
        border: 1px solid #484b51;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.85rem;
        transition: all 0.2s;
        font-weight: 600;
        color: #c1c2c5;
    }

    .radio-card input {
        display: none;
    }

    .radio-card.active {
        background: #4dabf7;
        color: white;
        border-color: #4dabf7;
    }

    .radio-card:hover:not(.active) {
        background: #484b51;
    }
</style>
