<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { Theme, CustomLayer } from "$lib/types";

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

    // Derived state for internal valid check?
    // Ideally validation is parent's job or shared store.

    const dispatch = createEventDispatcher();

    function triggerSearch() {
        dispatch("search");
    }

    function onDistanceChange() {
        dispatch("distanceChange", { distance }); // Update map circle
    }
</script>

<div class="controls-content">
    <!-- Location Section -->
    <div class="section">
        <h3><span class="icon">📍</span> Lieu</h3>
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
        </div>
    </div>

    <!-- Labels Section -->
    <div class="section">
        <h3><span class="icon">🏷️</span> Textes</h3>
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
    </div>

    <!-- Zoom/Distance -->
    <div class="section">
        <h3>
            <span class="icon">📏</span> Distance
            <span class="hint">({distance / 1000} km)</span>
        </h3>
        <div class="form-group">
            <input
                type="range"
                min="1000"
                max="100000"
                step="500"
                bind:value={distance}
                on:input={onDistanceChange}
            />
        </div>
    </div>

    <!-- Style Section -->
    <div class="section">
        <h3><span class="icon">🎨</span> Style</h3>
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
    </div>

    <!-- Custom Colors Toggle -->
    <div class="section">
        <h3><span class="icon">✏️</span> Personnalisation</h3>
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
                    />
                </div>
                <div class="color-item">
                    <label for="color-water">Eau</label>
                    <input
                        id="color-water"
                        type="color"
                        bind:value={customColors.water}
                    />
                </div>
                <div class="color-item">
                    <label for="color-parks">Parcs</label>
                    <input
                        id="color-parks"
                        type="color"
                        bind:value={customColors.parks}
                    />
                </div>
                <div class="color-item">
                    <label for="color-roads">Routes</label>
                    <input
                        id="color-roads"
                        type="color"
                        bind:value={customColors.roads}
                    />
                </div>
                <div class="color-item">
                    <label for="color-text">Texte</label>
                    <input
                        id="color-text"
                        type="color"
                        bind:value={customColors.text}
                    />
                </div>
            </div>
        {/if}
    </div>

    <!-- Additional Layers -->
    <div class="section">
        <h3><span class="icon">🛤️</span> Couches Sup.</h3>

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

    <!-- Export -->
    <div class="section">
        <h3><span class="icon">💾</span> Export</h3>
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
    </div>
</div>

<style>
    /* Reused styles from page.svelte */
    .section {
        margin-bottom: 28px;
    }
    h3 {
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
