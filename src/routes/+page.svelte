<script lang="ts">
    import { onMount, tick } from "svelte";
    import MapSelector from "$lib/components/MapSelector.svelte";
    import SidebarControls from "$lib/components/SidebarControls.svelte";
    import GenerationProgress from "$lib/components/GenerationProgress.svelte";
    import PosterPreview from "$lib/components/PosterPreview.svelte";

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
    // Labels
    let name = ""; // City label override
    let countryLabel = ""; // Country label override

    let distance = 10000;

    // Options
    let allThemes = false;
    let selectedTheme = "";
    let themes: Theme[] = [];

    // Export State
    let exportFormat = "png";

    // Custom Layers
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
            width: 0.5,
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

    // Mobile State
    let mobileMenuOpen = false;

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
    // We watch city/country and invoke flyToLocation via debounce
    // But to avoid loops with Map events, we should be careful.
    // For now, only explicit search via button (in Sidebar) triggers this.
    // SidebarControls dispatches "search".

    function handleSearch() {
        if (city && country && mapComponent) {
            mapComponent.flyToLocation(`${city}, ${country}`);
        }
    }

    // Handle map updates (Reverse Geocoding)
    function handleLocationSelect(event: CustomEvent) {
        const { city: c, country: co } = event.detail;
        if (c && c !== city) city = c;
        if (co && co !== country) country = co;
    }

    // Also update circle when distance changes (Sidebar -> Parent -> Map)
    // distance is 2-way bound. MapSelector takes {distance} prop. Svelte handles it.

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

        loading = false;
        abortController = null;

        if (result.success) {
            generatedFiles = result.files;
            // Scroll to results logic if needed
        } else {
            errorMsg = result.error || "Une erreur est survenue.";
        }
    }
</script>

<div class="app-container">
    <aside class="sidebar" class:open={mobileMenuOpen}>
        <header>
            <div class="logo">MAP<span class="highlight">POSTER</span></div>
            <p class="subtitle">Générateur d'affiches cartographiques</p>
            <button
                class="sidebar-close"
                on:click={() => (mobileMenuOpen = false)}>×</button
            >
        </header>

        <form class="controls" on:submit|preventDefault={handleSubmit}>
            <!-- Controls Component -->
            <SidebarControls
                bind:city
                bind:country
                bind:cityLabel={name}
                bind:countryLabel
                bind:distance
                bind:selectedTheme
                bind:allThemes
                {themes}
                bind:customLayers
                bind:customColorsEnabled
                bind:customColors
                bind:exportFormat
                on:search={handleSearch}
            />

            <!-- Action Area -->
            {#if loading}
                <GenerationProgress
                    {progressPercent}
                    {progressText}
                    on:cancel={cancelGeneration}
                />
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

        <!-- Preview List -->
        <PosterPreview files={generatedFiles} />

        <footer class="sidebar-footer">
            <a href="/about">
                <span class="icon">ℹ️</span> À propos & Crédits
            </a>
        </footer>
    </aside>

    <main class="map-area">
        <button class="mobile-toggle" on:click={() => (mobileMenuOpen = true)}>
            ⚙️ Paramètres
        </button>
        <MapSelector
            bind:this={mapComponent}
            {distance}
            themeId={selectedTheme}
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
        z-index: 1000;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.2);
    }

    header {
        padding: 24px;
        background: #1a1b1e;
        border-bottom: 1px solid #2c2e33;
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
        flex-shrink: 0; /* Let list take space */
        max-height: 60vh; /* Allow scroll if needed on small screens? */
        overflow-y: auto;
    }

    /* Scrollbar for controls area */
    .controls::-webkit-scrollbar {
        width: 6px;
    }
    .controls::-webkit-scrollbar-track {
        background: #2c2e33;
    }
    .controls::-webkit-scrollbar-thumb {
        background: #5c5f66;
        border-radius: 3px;
    }

    .btn-generate {
        width: 100%;
        padding: 12px;
        background: linear-gradient(135deg, #4dabf7 0%, #339af0 100%);
        color: white;
        border: none;
        border-radius: 6px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition:
            transform 0.1s,
            box-shadow 0.2s;
        margin-top: 10px;
    }

    .btn-generate:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(51, 154, 240, 0.3);
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
        z-index: 500;
        pointer-events: none;
    }

    .info-badge {
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(4px);
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.1);
        pointer-events: auto;
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
    /* Responsive Styles */
    @media (max-width: 768px) {
        .app-container {
            position: relative;
        }

        .sidebar {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            transform: translateX(-100%);
            transition: transform 0.3s ease-in-out;
        }

        .sidebar.open {
            transform: translateX(0);
        }

        /* Show mobile toggles */
        .mobile-toggle {
            display: flex !important;
        }

        .sidebar-close {
            display: block !important;
        }
    }

    .mobile-toggle {
        display: none;
        position: absolute;
        top: 20px;
        left: 20px;
        z-index: 600;
        background: #25262b;
        border: 1px solid #373a40;
        color: white;
        padding: 10px 16px;
        border-radius: 30px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        align-items: center;
        gap: 8px;
    }

    .sidebar-close {
        display: none;
        position: absolute;
        top: 20px;
        right: 20px;
        background: transparent;
        border: none;
        color: #909296;
        font-size: 1.5rem;
        cursor: pointer;
    }
</style>
