<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte";
    import type { Theme, CustomLayer, Preset } from "$lib/types";
    import { getPresets, savePreset, deletePreset } from "$lib/presets";

    // Props
    export let city: string;
    export let country: string;
    export let cityLabel: string; // was 'name'
    export let countryLabel: string;
    export let distance: number;
    export let selectedTheme: string;
    export let allThemes: boolean;
    export let themes: Theme[] = [];
    export let customLayers: CustomLayer[] = [];
    export let customColorsEnabled: boolean;
    export let customColors: any;
    export let exportFormat: string;
    // Print Settings
    export let dpi: number;
    export let margins: number;
    export let paperSize: string;
    export let width: number;
    export let height: number;

    const PAPER_SIZES = {
        A4: { w: 8.27, h: 11.69 },
        A3: { w: 11.69, h: 16.53 },
        "12x16": { w: 12.0, h: 16.0 },
        "30x40cm": { w: 11.81, h: 15.75 },
    };

    const PAPER_SIZE_LABELS: Record<string, string> = {
        A4: "A4 (21 x 29,7 cm)",
        A3: "A3 (29,7 x 42 cm)",
        "12x16": 'Standard (12x16")',
        "30x40cm": "30 x 40 cm",
        custom: "Personnalisé",
    };

    $: activePaperSize = (PAPER_SIZES as any)[paperSize] || {
        w: width,
        h: height,
    };
    $: paperRatio =
        activePaperSize && activePaperSize.h
            ? (activePaperSize.w / activePaperSize.h).toFixed(2)
            : "1.00";

    function onPaperSizeChange() {
        // @ts-ignore
        const size = PAPER_SIZES[paperSize];
        if (size) {
            width = size.w;
            height = size.h;
        }
    }
    // Ideally validation is parent's job or shared store.

    const dispatch = createEventDispatcher();

    function triggerSearch() {
        dispatch("search");
    }

    function onDistanceChange() {
        dispatch("distanceChange", { distance }); // Update map circle
    }

    // Validation
    $: isCityValid = city?.trim().length > 0;
    $: isCountryValid = country?.trim().length > 0;
    $: isDistanceValid = distance >= 1000 && distance <= 25000;
    // Meme plafond que le backend (100 Mpx) pour eviter un aller-retour 422.
    $: outputPixels = width * height * dpi * dpi;
    $: isOutputTooLarge = outputPixels > 100_000_000;

    // Presets Logic
    let presets: Preset[] = [];
    let newPresetName = "";

    onMount(() => {
        loadPresets();
    });

    function loadPresets() {
        presets = getPresets();
    }

    function saveCurrentAsPreset() {
        if (!newPresetName.trim()) return;
        const newPreset: Preset = {
            id: crypto.randomUUID(),
            name: newPresetName.trim(),
            createdAt: Date.now(),
            data: {
                city,
                country,
                cityLabel,
                countryLabel,
                distance,
                selectedTheme,
                allThemes,
                customLayers: JSON.parse(JSON.stringify(customLayers)), // deep copy
                customColorsEnabled,
                customColors: { ...customColors },
                exportFormat,
                dpi,
                margins,
                paperSize,
                width,
                height,
            },
        };
        savePreset(newPreset);
        newPresetName = "";
        loadPresets();
    }

    function loadPreset(p: Preset) {
        city = p.data.city;
        country = p.data.country;
        cityLabel = p.data.cityLabel;
        countryLabel = p.data.countryLabel;
        distance = p.data.distance;
        selectedTheme = p.data.selectedTheme;
        allThemes = p.data.allThemes;
        customLayers = p.data.customLayers || [];
        customColorsEnabled = p.data.customColorsEnabled;
        if (p.data.customColors) customColors = { ...p.data.customColors };
        exportFormat = p.data.exportFormat;
        // Backwards compat
        dpi = p.data.dpi || 300;
        margins = p.data.margins !== undefined ? p.data.margins : 0.5;
        paperSize = p.data.paperSize || "12x16";
        width = p.data.width || 12;
        height = p.data.height || 16;

        dispatch("search"); // Trigger search to update map
    }

    function removePreset(id: string) {
        if (confirm("Supprimer ce favori ?")) {
            deletePreset(id);
            loadPresets();
        }
    }
</script>

<div class="controls-content">
    <!-- Presets Section -->
    <details class="section">
        <summary class="section-summary">
            <span class="icon">⭐</span> Favoris
        </summary>
        <div class="presets-container">
            <div class="form-group row">
                <input
                    type="text"
                    bind:value={newPresetName}
                    placeholder="Nom du favori..."
                    style="flex:1"
                />
                <button
                    type="button"
                    class="btn-small"
                    on:click={saveCurrentAsPreset}
                    disabled={!newPresetName.trim()}>💾</button
                >
            </div>
            {#if presets.length === 0}
                <div class="empty-msg">Aucun favori enregistré.</div>
            {:else}
                <div class="presets-list">
                    {#each presets as p}
                        <div class="preset-item">
                            <button
                                type="button"
                                class="preset-name"
                                on:click={() => loadPreset(p)}
                                title="Charger">{p.name}</button
                            >
                            <button
                                class="btn-icon delete"
                                on:click|stopPropagation={() =>
                                    removePreset(p.id)}>🗑️</button
                            >
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    </details>

    <!-- Location Section -->
    <details class="section" open>
        <summary class="section-summary">
            <span class="icon">📍</span> Lieu
        </summary>
        <div class="form-group">
            <label for="city-input">Ville</label>
            <input
                id="city-input"
                type="text"
                bind:value={city}
                placeholder="Ex: Paris"
                on:keydown={(e) => e.key === "Enter" && triggerSearch()}
            />
            <button type="button" class="btn-search" on:click={triggerSearch}
                >🔍 Rechercher</button
            >
            {#if !isCityValid && city !== undefined}
                <span class="error-msg">Veuillez entrer une ville</span>
            {/if}
        </div>
        <div class="form-group">
            <label for="country-input">Pays</label>
            <input
                id="country-input"
                type="text"
                bind:value={country}
                placeholder="Ex: France"
                on:keydown={(e) => e.key === "Enter" && triggerSearch()}
            />
            {#if !isCountryValid && country !== undefined}
                <span class="error-msg">Veuillez entrer un pays</span>
            {/if}
        </div>
    </details>

    <!-- Labels Section -->
    <details class="section" open>
        <summary class="section-summary">
            <span class="icon">🏷️</span> Textes
        </summary>
        <div class="grid-2">
            <div class="form-group">
                <label for="city-label">Titre (Ville)</label>
                <input
                    id="city-label"
                    type="text"
                    bind:value={cityLabel}
                    placeholder={city}
                />
            </div>
            <div class="form-group">
                <label for="country-label">Sous-titre (Pays)</label>
                <input
                    id="country-label"
                    type="text"
                    bind:value={countryLabel}
                    placeholder={country}
                />
            </div>
        </div>
    </details>

    <!-- Zoom/Distance -->
    <details class="section" open>
        <summary class="section-summary">
            <span class="icon">📏</span> Distance
            <span class="hint">({distance / 1000} km)</span>
        </summary>
        <div class="form-group">
            <input
                type="range"
                min="1000"
                max="25000"
                step="500"
                bind:value={distance}
                on:input={onDistanceChange}
                aria-label="Distance de génération de la carte"
            />
            {#if !isDistanceValid}
                <span class="error-msg"
                    >La distance doit être entre 1 km et 25 km (limite de
                    mémoire du worker)</span
                >
            {/if}
        </div>
    </details>

    <!-- Style Section -->
    <details class="section" open>
        <summary class="section-summary">
            <span class="icon">🎨</span> Style
        </summary>
        <div class="form-group">
            <label for="theme-select">Thème</label>
            {#if themes.length === 0}
                <div class="loading-themes">Chargement...</div>
            {:else}
                <select
                    id="theme-select"
                    bind:value={selectedTheme}
                    disabled={allThemes}
                >
                    {#each themes as theme}
                        <option value={theme.id}>
                            {theme.name}
                        </option>
                    {/each}
                </select>
            {/if}
        </div>

        <!-- Toggle All Themes (Optional feature) -->
        <div class="form-group checkbox-group">
            <label class="toggle">
                <input type="checkbox" bind:checked={allThemes} />
                <span class="slider"></span>
                <span class="label-text">Générer tous les thèmes</span>
            </label>
        </div>
    </details>

    <!-- Custom Colors Toggle -->
    <details class="section">
        <summary class="section-summary">
            <span class="icon">✏️</span> Personnalisation
        </summary>
        <div class="form-group checkbox-group">
            <label class="toggle">
                <input type="checkbox" bind:checked={customColorsEnabled} />
                <span class="slider"></span>
                <span class="label-text">Couleurs personnalisées</span>
            </label>
        </div>

        {#if customColorsEnabled}
            <div class="color-grid">
                <div class="color-item">
                    <label for="color-bg">Fond</label>
                    <input
                        id="color-bg"
                        type="color"
                        bind:value={customColors.bg}
                        aria-label="Couleur de fond"
                    />
                </div>
                <div class="color-item">
                    <label for="color-water">Eau</label>
                    <input
                        id="color-water"
                        type="color"
                        bind:value={customColors.water}
                        aria-label="Couleur de l'eau"
                    />
                </div>
                <div class="color-item">
                    <label for="color-parks">Parcs</label>
                    <input
                        id="color-parks"
                        type="color"
                        bind:value={customColors.parks}
                        aria-label="Couleur des parcs"
                    />
                </div>
                <div class="color-item">
                    <label for="color-roads">Routes</label>
                    <input
                        id="color-roads"
                        type="color"
                        bind:value={customColors.roads}
                        aria-label="Couleur des routes"
                    />
                </div>
                <div class="color-item">
                    <label for="color-text">Texte</label>
                    <input
                        id="color-text"
                        type="color"
                        bind:value={customColors.text}
                        aria-label="Couleur du texte"
                    />
                </div>
            </div>
        {/if}
    </details>

    <!-- Additional Layers -->
    <details class="section">
        <summary class="section-summary">
            <span class="icon">🛤️</span> Couches Sup.
        </summary>

        {#each customLayers as layer}
            <div class="layer-control">
                <div class="form-group checkbox-group">
                    <label class="toggle">
                        <input type="checkbox" bind:checked={layer.enabled} />
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
                            aria-label={`Couleur pour ${layer.label}`}
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
                                aria-label={`Épaisseur pour ${layer.label}`}
                            />
                            <span class="value">{layer.width}</span>
                        </div>
                    </div>
                {/if}
            </div>
        {/each}
    </details>

    <!-- Print Settings (New) -->
    <details class="section">
        <summary class="section-summary">
            <span class="icon">🖨️</span> Impression
        </summary>
        <div class="form-group">
            <label for="paper-select">Format Papier</label>
            <select
                id="paper-select"
                bind:value={paperSize}
                on:change={onPaperSizeChange}
            >
                <option value="A4">A4 (21 x 29.7cm)</option>
                <option value="A3">A3 (29.7 x 42cm)</option>
                <option value="12x16">Standard (12x16")</option>
                <option value="30x40cm">30 x 40 cm</option>
                <option value="custom">Personnalisé</option>
            </select>
        </div>

        <div class="paper-preview">
            <div class="paper-preview-header">
                <span>Aperçu du ratio</span>
                <span class="paper-preview-meta"
                    >{PAPER_SIZE_LABELS[paperSize] ||
                        `Custom ${width}" x ${height}"`}</span
                >
            </div>
            <div class="paper-preview-frame">
                <div
                    class="paper-preview-sheet"
                    style={`aspect-ratio: ${paperRatio};`}
                ></div>
            </div>
            <div class="paper-preview-foot">
                Ratio: {paperRatio}
            </div>
        </div>

        {#if paperSize === "custom"}
            <div class="grid-2">
                <div class="form-group">
                    <label for="w-input">Largeur (pouces)</label>
                    <input
                        id="w-input"
                        type="number"
                        step="0.1"
                        min="1"
                        max="40"
                        bind:value={width}
                        aria-label="Largeur personnalisée en pouces"
                    />
                </div>
                <div class="form-group">
                    <label for="h-input">Hauteur (pouces)</label>
                    <input
                        id="h-input"
                        type="number"
                        step="0.1"
                        min="1"
                        max="40"
                        bind:value={height}
                        aria-label="Hauteur personnalisée en pouces"
                    />
                </div>
            </div>
        {/if}

        <div class="grid-2">
            <div class="form-group">
                <label for="dpi-select">Qualité (DPI)</label>
                <select id="dpi-select" bind:value={dpi}>
                    <option value={150}>150 (Web/Draft)</option>
                    <option value={300}>300 (Print)</option>
                    <option value={600}>600 (High-Res)</option>
                </select>
            </div>
            {#if isOutputTooLarge}
                <span class="error-msg"
                    >Résolution trop élevée ({Math.round(outputPixels / 1_000_000)}
                    Mpx, maximum 100 Mpx). Réduisez les dimensions ou le
                    DPI.</span
                >
            {/if}
            <div class="form-group">
                <label for="margin-input">Marge ({margins}")</label>
                <input
                    id="margin-input"
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    bind:value={margins}
                    aria-label="Marge d'impression"
                />
            </div>
        </div>
    </details>

    <!-- Export -->
    <details class="section">
        <summary class="section-summary">
            <span class="icon">💾</span> Export
        </summary>
        <div class="form-group">
            <span class="label">Format de fichier</span>
            <div class="format-idx">
                {#each ["png", "svg", "pdf"] as f}
                    <label
                        class="radio-card {exportFormat === f ? 'active' : ''}"
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
    </details>
</div>

<style>
    /* Reused styles from page.svelte */
    .section {
        margin-bottom: 28px;
    }
    .section-summary {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #909296;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 1px solid #373a40;
        padding-bottom: 8px;
        cursor: pointer;
        list-style: none;
    }
    .section-summary::-webkit-details-marker {
        display: none;
    }
    .section-summary::marker {
        content: "";
    }
    details.section[open] > .section-summary {
        color: #c1c2c5;
        border-bottom-color: #4dabf7;
    }
    details.section:not([open]) > .section-summary {
        margin-bottom: 0;
        border-bottom: none;
    }
    .icon {
        font-size: 1.1rem;
    }
    .form-group {
        margin-bottom: 16px;
    }
    label,
    .label {
        display: block;
        font-size: 0.85rem;
        margin-bottom: 6px;
        color: #c1c2c5;
        font-weight: 500;
    }
    input[type="text"],
    select {
        width: 100%;
        padding: 10px;
        background: #25262b;
        border: 1px solid #373a40;
        border-radius: 6px;
        color: white;
        font-size: 0.95rem;
        transition: all 0.2s;
        box-sizing: border-box;
    }
    input[type="text"]:focus,
    select:focus {
        outline: none;
        border-color: #4dabf7;
        box-shadow: 0 0 0 2px rgba(77, 171, 247, 0.2);
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
    .grid-2 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }
    input[type="range"] {
        width: 100%;
        height: 6px;
        background: #373a40;
        border-radius: 3px;
        outline: none;
        appearance: none;
    }
    input[type="range"]::-webkit-slider-thumb {
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
        transition: 0.3s;
        margin-right: 10px;
    }
    .slider:before {
        position: absolute;
        content: "";
        height: 16px;
        width: 16px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: 0.3s;
        border-radius: 50%;
    }
    input:checked + .slider {
        background-color: #4dabf7;
    }
    input:checked + .slider:before {
        transform: translateX(18px);
    }
    .label-text {
        font-size: 0.9rem;
        color: #e0e0e0;
    }
    .checkbox-group {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
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
        width: 100%;
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
    .layer-control {
        margin-bottom: 12px;
    }
    .layer-settings {
        display: flex;
        gap: 12px;
        align-items: center;
        margin-top: 8px;
        margin-left: 52px;
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
    .format-idx {
        display: flex;
        gap: 8px;
        margin-top: 8px;
    }
    .paper-preview {
        background: #1f2024;
        border: 1px solid #2c2e33;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 16px;
    }
    .paper-preview-header {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        color: #adb5bd;
        margin-bottom: 10px;
        gap: 12px;
        flex-wrap: wrap;
    }
    .paper-preview-meta {
        color: #74c0fc;
        font-weight: 600;
    }
    .paper-preview-frame {
        display: flex;
        justify-content: center;
        align-items: center;
        background: #25262b;
        border-radius: 6px;
        padding: 12px;
        min-height: 120px;
    }
    .paper-preview-sheet {
        width: 100%;
        max-width: 140px;
        background: #3b3f46;
        border: 1px solid #4dabf7;
        border-radius: 4px;
        box-shadow: inset 0 0 0 2px rgba(77, 171, 247, 0.15);
    }
    .paper-preview-foot {
        margin-top: 8px;
        font-size: 0.75rem;
        color: #909296;
        text-align: center;
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
    .error-msg {
        color: #fa5252;
        font-size: 0.75rem;
        margin-top: 4px;
        display: block;
    }
    .btn-small {
        padding: 8px;
        background: #373a40;
        border: 1px solid #484b51;
        color: white;
        border-radius: 6px;
        cursor: pointer;
        margin-left: 8px;
    }
    .btn-small:disabled {
        opacity: 0.5;
        cursor: default;
    }
    .row {
        display: flex;
        align-items: center;
    }
    .presets-list {
        display: flex;
        flex-direction: column;
        gap: 6px;
        max-height: 150px;
        overflow-y: auto;
    }
    .preset-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #2c2e33;
        padding: 8px;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    .preset-name {
        cursor: pointer;
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        background: none;
        border: none;
        padding: 0;
        font: inherit;
        color: inherit;
        text-align: left;
    }
    .preset-name:hover {
        color: #4dabf7;
    }
    .btn-icon {
        background: none;
        border: none;
        cursor: pointer;
        padding: 4px;
        font-size: 0.9rem;
    }
    .btn-icon.delete:hover {
        transform: scale(1.1);
    }
    .empty-msg {
        font-size: 0.8rem;
        color: #909296;
        font-style: italic;
    }
    details.section {
        padding-bottom: 12px;
        border-bottom: 1px solid #2c2e33;
    }
    details.section:last-child {
        border-bottom: none;
    }
    details.section > :not(summary) {
        margin-top: 12px;
    }

    /* ---------------------------------------------------------------------
       Surcouche visuelle moderne : surfaces, focus, switches et cartes.
       Les variables viennent du layout global.
       --------------------------------------------------------------------- */
    .section {
        margin-bottom: 8px;
    }

    details.section {
        padding-bottom: 0;
        border-bottom: none;
    }

    details.section[open] {
        padding: 0 12px 10px;
        border: 1px solid var(--border);
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.018);
    }

    .section-summary {
        padding: 10px 12px;
        margin-bottom: 8px;
        border: 1px solid transparent;
        border-radius: 10px;
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        transition:
            background 0.18s ease,
            color 0.18s ease;
    }

    .section-summary:hover {
        background: rgba(255, 255, 255, 0.04);
        color: var(--text);
    }

    .section-summary::after {
        content: "";
        width: 7px;
        height: 7px;
        margin-left: auto;
        border-right: 1.5px solid currentColor;
        border-bottom: 1.5px solid currentColor;
        transform: rotate(45deg);
        opacity: 0.7;
        transition: transform 0.2s ease;
    }

    details.section[open] > .section-summary {
        margin-bottom: 12px;
        padding: 10px 0 12px;
        border-bottom: 1px solid var(--border);
        border-radius: 0;
        color: var(--text);
    }

    details.section[open] > .section-summary::after {
        transform: rotate(225deg);
    }

    details.section > :not(summary) {
        margin-top: 0;
    }

    .form-group {
        margin-bottom: 14px;
    }

    label,
    .label,
    .color-item label {
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 500;
    }

    input[type="text"],
    input[type="number"],
    select {
        background: var(--panel-2);
        border-color: var(--border);
        border-radius: 10px;
        color: var(--text);
    }

    input[type="text"]:focus,
    input[type="number"]:focus,
    select:focus {
        border-color: var(--accent);
        box-shadow: 0 0 0 3px rgba(103, 232, 249, 0.12);
    }

    .btn-search,
    .btn-small {
        background: var(--panel-2);
        border-color: var(--border);
        border-radius: 10px;
        color: var(--text);
    }

    .btn-search:hover,
    .btn-small:hover:not(:disabled) {
        background: var(--panel);
        border-color: var(--border-strong);
        color: var(--accent);
    }

    input[type="range"] {
        background: var(--border);
        border-radius: 999px;
    }

    input[type="range"]::-webkit-slider-thumb {
        background: var(--accent);
        box-shadow: 0 0 0 4px rgba(103, 232, 249, 0.14);
    }

    .slider {
        background-color: var(--border-strong);
    }

    input:checked + .slider {
        background-color: var(--accent);
    }

    .label-text {
        color: var(--text);
    }

    .layer-settings {
        background: var(--panel-2);
        border: 1px solid var(--border);
        border-radius: 10px;
    }

    .paper-preview {
        background: var(--panel-2);
        border-color: var(--border);
        border-radius: 12px;
    }

    .paper-preview-frame {
        background: var(--panel);
        border-radius: 9px;
    }

    .paper-preview-sheet {
        background: var(--panel-2);
        border-color: rgba(103, 232, 249, 0.45);
        box-shadow: inset 0 0 0 2px rgba(103, 232, 249, 0.1);
    }

    .paper-preview-meta {
        color: var(--accent);
    }

    .radio-card {
        background: var(--panel-2);
        border-color: var(--border);
        border-radius: 10px;
        color: var(--muted);
    }

    .radio-card.active {
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        border-color: transparent;
        color: #06121a;
    }

    .radio-card:hover:not(.active) {
        background: var(--panel);
        border-color: var(--border-strong);
        color: var(--text);
    }

    .preset-item {
        background: var(--panel-2);
        border: 1px solid var(--border);
        border-radius: 10px;
    }

    .preset-name:hover {
        color: var(--accent);
    }

    .error-msg {
        color: var(--danger);
        line-height: 1.4;
    }

    .empty-msg {
        color: var(--muted);
    }

    /* Confort tactile : cibles >= 44 px et champs a 16 px pour eviter le
       zoom automatique de Safari iOS au focus. */
    @media (max-width: 768px) {
        input[type="text"],
        input[type="number"],
        select {
            min-height: 44px;
            font-size: 16px;
        }

        .btn-search,
        .btn-small,
        .section-summary,
        .toggle,
        .preset-name,
        .btn-icon {
            min-height: 44px;
        }

        .btn-small,
        .btn-icon {
            min-width: 44px;
        }

        .radio-card {
            min-height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .layer-settings {
            margin-left: 0;
        }

        input[type="range"] {
            height: 8px;
        }

        input[type="range"]::-webkit-slider-thumb {
            width: 24px;
            height: 24px;
        }

        .color-item input[type="color"] {
            height: 44px;
        }
    }
</style>
