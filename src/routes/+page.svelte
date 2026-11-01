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
    import { t, getStatusLabel } from "$lib/i18n";
    import { fade } from "svelte/transition"; // Added for mobile badge transition if needed

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
    // Export State
    let exportFormat = "png";
    let dpi = 300;
    let margins = 0.5;
    let paperSize = "12x16";
    let width = 12.0;
    let height = 16.0;

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
    let progressEtaText = "";
    let generationStart = 0;
    let smoothedEtaSeconds: number | null = null;
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

    // Handle map errors
    function handleMapError(event: CustomEvent) {
        errorMsg = event.detail.message;
        // Auto-hide after 5s if desired, or keep it.
        setTimeout(() => {
            errorMsg = "";
        }, 5000);
    }

    // Also update circle when distance changes (Sidebar -> Parent -> Map)
    // distance is 2-way bound. MapSelector takes {distance} prop. Svelte handles it.

    function cancelGeneration() {
        if (abortController) {
            abortController.abort();
            abortController = null;
            loading = false;
            progressText = t.errors.generationCancelled;
            progressEtaText = "";
            smoothedEtaSeconds = null;
        }
    }

    function estimateTotalSeconds() {
        const sizeFactor = Math.max(1, (width * height) / 200);
        const distanceFactor = Math.max(1, distance / 10000);
        const dpiFactor = Math.max(1, dpi / 300);
        const themeFactor = allThemes ? 2.2 : 1;
        return Math.round(
            18 * sizeFactor * distanceFactor * dpiFactor * themeFactor,
        );
    }

    function formatDuration(seconds: number) {
        const clamped = Math.max(0, Math.round(seconds));
        const mins = Math.floor(clamped / 60);
        const secs = clamped % 60;
        if (mins <= 0) return `${secs}s`;
        return `${mins}m ${secs}s`;
    }

    async function handleSubmit() {
        if (!city || !country) return;

        loading = true;
        errorMsg = "";
        generatedFiles = [];
        progressPercent = 0;
        progressText = "Démarrage...";
        progressEtaText = "";
        generationStart = Date.now();
        smoothedEtaSeconds = null;

        abortController = new AbortController();

        const payload: GenerationRequest = {
            city,
            country,
            name_label: name || undefined,
            country_label: countryLabel || undefined,
            distance,
            style: !allThemes ? selectedTheme : undefined,
            all_themes: allThemes,
            custom_layers: customLayers, // Send custom layers
            custom_colors: customColorsEnabled ? customColors : undefined,

            format: exportFormat,
            dpi,
            margins,
            paper_size: paperSize,
            width,
            height,
        };

        const result = await generatePoster(
            payload,
            (percent, text) => {
                progressPercent = percent;
                // Use getStatusLabel to translate or fallback
                progressText = getStatusLabel(text);

                if (percent > 0 && percent < 100) {
                    const elapsed = (Date.now() - generationStart) / 1000;
                    const progressRatio = percent / 100;
                    let remaining = 0;

                    if (progressRatio >= 0.06) {
                        const estimatedTotal = elapsed / progressRatio;
                        remaining = Math.max(0, estimatedTotal - elapsed);
                    } else {
                        const fallbackTotal = estimateTotalSeconds();
                        remaining = Math.max(0, fallbackTotal - elapsed);
                    }

                    smoothedEtaSeconds =
                        smoothedEtaSeconds === null
                            ? remaining
                            : smoothedEtaSeconds * 0.7 + remaining * 0.3;

                    progressEtaText = `Temps restant estimé : ${formatDuration(
                        smoothedEtaSeconds,
                    )}`;
                } else {
                    progressEtaText = "";
                }
            },
            abortController.signal,
        );

        loading = false;
        abortController = null;

        if (result.success) {
            generatedFiles = result.files;
            // Scroll to results logic if needed
        } else {
            errorMsg = result.error || t.errors.unknownError;
        }
    }

    // Validation
    $: isValid =
        city &&
        city.trim().length > 0 &&
        country &&
        country.trim().length > 0 &&
        distance >= 1000 &&
        distance <= 25000 &&
        width >= 1 &&
        width <= 40 &&
        height >= 1 &&
        height <= 40 &&
        width * height * dpi * dpi <= 100_000_000;
</script>

<div class="app-container">
    <aside class="sidebar" class:open={mobileMenuOpen}>
        <header>
            <div class="logo">MAP<span class="highlight">POSTER</span></div>
            <p class="subtitle">Générateur d'affiches cartographiques</p>
            <div class="header-meta">
                <span class="status-dot"></span>
                OpenStreetMap · aperçu live
            </div>
            <button
                class="sidebar-close"
                aria-label="Fermer les paramètres"
                on:click={() => (mobileMenuOpen = false)}>×</button
            >
        </header>

        <form
            class="controls"
            aria-busy={loading}
            on:submit|preventDefault={handleSubmit}
        >
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
                bind:dpi
                bind:margins
                bind:paperSize
                bind:width
                bind:height
                on:search={handleSearch}
            />

            <!-- Action Area -->
            {#if loading}
                <GenerationProgress
                    {progressPercent}
                    {progressText}
                    etaText={progressEtaText}
                    on:cancel={cancelGeneration}
                />
            {:else}
                <button type="submit" class="btn-generate" disabled={!isValid}>
                    ✨ Générer l'affiche
                </button>
            {/if}

            {#if errorMsg}
                <div class="error-banner" role="alert">
                    {errorMsg}
                </div>
            {/if}

            <!-- Preview List (Inside Scrollable Area) -->
            <PosterPreview files={generatedFiles} />
        </form>

        <footer class="sidebar-footer">
            <div class="credits">
                <span class="made-by"
                    >Développé par <a
                        href="https://github.com/simongrossi"
                        target="_blank"
                        rel="noopener">Simon Grossi</a
                    ></span
                >
            </div>
            <a href="/about" class="about-link">
                <span class="icon">ℹ️</span> À propos & Crédits
            </a>
        </footer>
    </aside>

    <main class="map-area">
        <button
            class="mobile-toggle"
            aria-label="Ouvrir les paramètres"
            on:click={() => (mobileMenuOpen = true)}
        >
            ⚙️ Paramètres
            {#if !mobileMenuOpen}
                <span class="settings-dot"></span>
            {/if}
        </button>
        <MapSelector
            bind:this={mapComponent}
            {distance}
            themeId={selectedTheme}
            on:locationSelect={handleLocationSelect}
            on:error={handleMapError}
        />
        <div class="map-overlay">
            <div class="info-badge">Aperçu de la zone de couverture</div>
        </div>
    </main>
</div>

<style>
    .app-container {
        display: flex;
        height: 100vh;
        height: 100dvh;
        width: 100%;
        overflow: hidden;
        background: var(--bg);
    }

    /* Sidebar Styles */
    .sidebar {
        width: 380px;
        background: linear-gradient(
            180deg,
            rgba(20, 25, 34, 0.98),
            rgba(10, 13, 18, 0.99)
        );
        border-right: 1px solid var(--border);
        display: flex;
        flex-direction: column;
        z-index: 1000;
        box-shadow: 24px 0 80px rgba(0, 0, 0, 0.35);
    }

    header {
        position: relative;
        padding: 26px 24px 22px;
        background: transparent;
        border-bottom: 1px solid var(--border);
    }

    .logo {
        font-size: 1.55rem;
        font-weight: 800;
        color: var(--text);
        letter-spacing: -0.04em;
        line-height: 1;
    }

    .highlight {
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }

    .subtitle {
        color: var(--muted);
        font-size: 0.82rem;
        margin: 8px 0 0 0;
    }

    .header-meta {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        margin-top: 14px;
        padding: 5px 9px;
        border: 1px solid rgba(103, 232, 249, 0.18);
        background: rgba(103, 232, 249, 0.06);
        border-radius: 999px;
        color: var(--muted);
        font-size: 0.72rem;
        font-weight: 500;
    }

    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--success);
        box-shadow: 0 0 0 4px rgba(52, 211, 153, 0.12);
        animation: pulse 2.4s ease-in-out infinite;
    }

    @keyframes pulse {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.5;
        }
    }

    .controls {
        padding: 22px 24px 28px;
        flex: 1;
        overflow-y: auto;
        min-height: 0;
    }

    /* Scrollbar for controls area */
    .controls::-webkit-scrollbar {
        width: 6px;
    }
    .controls::-webkit-scrollbar-track {
        background: transparent;
    }
    .controls::-webkit-scrollbar-thumb {
        background: var(--border-strong);
        border-radius: 999px;
    }

    .btn-generate {
        width: 100%;
        padding: 14px 16px;
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        color: #06121a;
        border: none;
        border-radius: 12px;
        font-size: 1rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        cursor: pointer;
        transition:
            transform 0.16s ease,
            box-shadow 0.2s ease,
            filter 0.2s ease;
        margin-top: 14px;
        box-shadow: 0 14px 34px rgba(96, 165, 250, 0.22);
    }

    .btn-generate:hover:not(:disabled) {
        transform: translateY(-2px);
        filter: brightness(1.06);
        box-shadow: 0 18px 44px rgba(96, 165, 250, 0.3);
    }

    .btn-generate:active:not(:disabled) {
        transform: translateY(0);
    }

    .btn-generate:disabled {
        cursor: not-allowed;
        background: var(--panel-2);
        color: var(--muted);
        box-shadow: none;
    }

    .error-banner {
        margin-top: 16px;
        padding: 12px 14px;
        background: rgba(251, 113, 133, 0.1);
        border: 1px solid rgba(251, 113, 133, 0.28);
        color: #fecdd3;
        border-radius: 10px;
        font-size: 0.88rem;
        line-height: 1.45;
    }

    /* Map Area */
    .map-area {
        flex: 1;
        min-width: 0;
        position: relative;
        background: var(--bg);
    }

    .map-overlay {
        position: absolute;
        top: 20px;
        right: 20px;
        z-index: 500;
        pointer-events: none;
    }

    .info-badge {
        background: rgba(10, 13, 18, 0.72);
        backdrop-filter: blur(14px);
        padding: 8px 14px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 500;
        color: var(--text);
        border: 1px solid rgba(255, 255, 255, 0.09);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.28);
        pointer-events: auto;
        cursor: default;
    }

    .sidebar-footer {
        padding: 20px 24px 22px;
        border-top: 1px solid var(--border);
        margin-top: auto;
    }

    .sidebar-footer a {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--muted);
        text-decoration: none;
        font-size: 0.84rem;
        transition: color 0.2s;
    }

    .sidebar-footer a:hover {
        color: var(--accent);
    }

    .credits {
        margin-bottom: 8px;
        font-size: 0.78rem;
        color: var(--muted);
    }

    .made-by a {
        color: var(--text);
        text-decoration: underline;
        text-decoration-color: rgba(255, 255, 255, 0.25);
        text-underline-offset: 3px;
        font-weight: 500;
    }

    .made-by a:hover {
        color: var(--accent);
        text-decoration-color: var(--accent);
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

        /* Le badge et le zoom Leaflet sont masqués sur mobile : le bouton
           Paramètres occupe déjà le coin supérieur gauche et la carte se
           manipule au doigt. */
        .map-overlay {
            display: none;
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
        background: rgba(13, 17, 22, 0.78);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: var(--text);
        padding: 10px 16px;
        border-radius: 999px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        align-items: center;
        gap: 8px;
        animation: bounce 2.8s ease-in-out infinite;
    }

    .settings-dot {
        width: 8px;
        height: 8px;
        background: var(--danger);
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 0 4px rgba(251, 113, 133, 0.12);
    }

    @keyframes bounce {
        0%,
        20%,
        50%,
        80%,
        100% {
            transform: translateY(0);
        }
        40% {
            transform: translateY(-5px);
        }
        60% {
            transform: translateY(-3px);
        }
    }

    .sidebar-close {
        display: none;
        position: absolute;
        top: 20px;
        right: 18px;
        background: transparent;
        border: none;
        color: var(--muted);
        font-size: 1.5rem;
        cursor: pointer;
    }

    @media (min-width: 769px) and (max-width: 1100px) {
        .sidebar {
            width: 350px;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .settings-dot,
        .mobile-toggle,
        .status-dot {
            animation: none;
        }

        * {
            transition-duration: 0.01ms !important;
        }
    }
</style>
