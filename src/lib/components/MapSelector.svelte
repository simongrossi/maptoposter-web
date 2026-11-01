<script lang="ts">
    import { onMount, createEventDispatcher } from "svelte";
    import { browser } from "$app/environment";
    import type * as L from "leaflet"; // Import definitions
    import { t } from "$lib/i18n";

    export let initialDefaults = { lat: 48.8566, lng: 2.3522 }; // Paris default
    export let distance: number = 10000;
    export let themeId: string = "standard";

    const dispatch = createEventDispatcher();
    let mapElement: HTMLElement;

    // Leaflet instances with types
    let map: L.Map;
    let tileLayer: L.TileLayer; // Track layer to swap it
    let previewRect: L.Rectangle;
    let marker: L.Marker;
    let leaflet: typeof L; // Runtime library
    let tileTone: "standard" | "dark" | "light" = "standard";
    let locating = false;

    // Poster config mirroring backend default (12x16 inch = 0.75 aspect)
    const ASPECT_RATIO = 12 / 16;

    // Tuiles de prévisualisation : OSM standard uniquement, aucune clé API.
    // Les thèmes sombres/clair sont obtenus par un filtre CSS sur le tile pane.
    const OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
    const OSM_ATTRIBUTION =
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors';

    onMount(async () => {
        if (browser) {
            const module = await import("leaflet");
            leaflet = module.default || module;
            await import("leaflet/dist/leaflet.css");
            initMap();
        }
    });

    // Watch distance
    $: if (map && distance && previewRect && marker) {
        updatePreviewRectangle(marker.getLatLng());
    }

    // Watch Theme
    $: if (map && themeId && leaflet) {
        updateTileLayer();
    }

    function updateTileLayer() {
        if (!map || !leaflet) return;

        const isDark =
            !!themeId &&
            (themeId.includes("noir") || themeId.includes("dark"));
        const isLight =
            !!themeId &&
            (themeId.includes("white") ||
                themeId.includes("light") ||
                themeId.includes("minimal"));

        tileTone = isDark ? "dark" : isLight ? "light" : "standard";

        if (tileLayer) {
            map.removeLayer(tileLayer);
        }

        // Une seule source de tuiles, libre et sans clé. Le rendu "noir" ou
        // "minimal" ne change que le filtre CSS, pas le fournisseur.
        tileLayer = leaflet
            .tileLayer(OSM_TILE_URL, {
                attribution: OSM_ATTRIBUTION,
                maxZoom: 19,
            })
            .addTo(map);

        // Ensure markers/rects stay on top? TileLayers usually go on background (z-index 1).
        // If needed: tileLayer.bringToBack();
        tileLayer.bringToBack();
    }

    function initMap() {
        if (!mapElement) return;

        // Fix 404 on marker icons
        // @ts-ignore
        delete leaflet.Icon.Default.prototype._getIconUrl;
        leaflet.Icon.Default.mergeOptions({
            iconRetinaUrl:
                "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
            iconUrl:
                "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
            shadowUrl:
                "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
        });

        // Create map
        map = leaflet
            .map(mapElement)
            .setView([initialDefaults.lat, initialDefaults.lng], 10);

        // Init Tile Layer
        updateTileLayer();

        // Marker (draggable center)
        marker = leaflet
            .marker([initialDefaults.lat, initialDefaults.lng], {
                draggable: true,
            })
            .addTo(map);

        // Setup init rectangle at default position
        const bounds = calculateBounds(
            new leaflet.LatLng(initialDefaults.lat, initialDefaults.lng),
        );
        previewRect = leaflet
            .rectangle(bounds, {
                color: "#4dabf7",
                weight: 2,
                fillColor: "#4dabf7",
                fillOpacity: 0.15,
                dashArray: "5, 5",
            })
            .addTo(map);

        // Events
        marker.on("drag", () => {
            updatePreviewRectangle(marker.getLatLng());
        });
        marker.on("dragend", handleMarkerDragEnd);

        map.on("click", (e: L.LeafletMouseEvent) => {
            marker.setLatLng(e.latlng);
            updatePreviewRectangle(e.latlng);
            handleMarkerDragEnd();
        });

        // Trigger initial lookup
        lookupAddress(initialDefaults.lat, initialDefaults.lng);
    }

    function calculateBounds(center: L.LatLng): L.LatLngBoundsExpression {
        // Logic mirroring backend/renderer.py crop
        // "distance" arg is roughly the "radius" or "half-size" of the major axis.

        // Since ASPECT_RATIO = 0.75 (Width < Height), Height is the major dimension.
        // half_height_meters = distance
        // half_width_meters = distance * ASPECT_RATIO

        const halfHeightMeters = distance;
        const halfWidthMeters = distance * ASPECT_RATIO;

        // Convert to degrees (Approximation)
        // 1 deg Lat ~= 111,111 meters
        const latOffset = halfHeightMeters / 111111;

        // 1 deg Lon ~= 111,111 * cos(lat) meters
        const latRad = center.lat * (Math.PI / 180);
        const lonOffset = halfWidthMeters / (111111 * Math.cos(latRad));

        const southWest = leaflet.latLng(
            center.lat - latOffset,
            center.lng - lonOffset,
        );
        const northEast = leaflet.latLng(
            center.lat + latOffset,
            center.lng + lonOffset,
        );

        return leaflet.latLngBounds(southWest, northEast);
    }

    function updatePreviewRectangle(center: L.LatLng) {
        if (!previewRect) return;
        const bounds = calculateBounds(center);
        previewRect.setBounds(bounds);
    }

    function handleMarkerDragEnd() {
        if (!marker) return;
        const latlng = marker.getLatLng();
        map.panTo(latlng);
        lookupAddress(latlng.lat, latlng.lng);
    }

    // Debounce lookup to avoid spamming Nominatim
    let timeout: any;
    let isProgrammaticMove = false;

    export async function flyToLocation(query: string) {
        if (!map) return;

        try {
            // Use Backend Proxy to avoid CORS/User-Agent issues
            const url = `/api/geocode?q=${encodeURIComponent(query)}`;
            const res = await fetch(url);
            const data = await res.json();

            if (data && data.length > 0) {
                const lat = parseFloat(data[0].lat);
                const lon = parseFloat(data[0].lon);

                isProgrammaticMove = true;
                const newLatLng = new leaflet.LatLng(lat, lon);
                marker.setLatLng(newLatLng);
                updatePreviewRectangle(newLatLng);
                map.setView(newLatLng, 12);

                // Allow events to settle
                setTimeout(() => {
                    isProgrammaticMove = false;
                }, 1000);
            } else {
                dispatch("error", { message: t.errors.locationNotFound });
                console.warn("Geocoding returned no results for:", query);
            }
        } catch (e) {
            console.error("Forward geocoding failed", e);
            dispatch("error", { message: t.errors.geocodingError });
        }
    }

    function lookupAddress(lat: number, lng: number, force = false) {
        if (isProgrammaticMove && !force) return;

        if (timeout) clearTimeout(timeout);
        timeout = setTimeout(async () => {
            try {
                const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`;
                const res = await fetch(url, {
                    headers: { "User-Agent": "MapToPosterClient/1.0" },
                });
                const data = await res.json();

                if (data && data.address) {
                    const city =
                        data.address.city ||
                        data.address.town ||
                        data.address.village ||
                        data.address.municipality ||
                        data.address.county ||
                        "";
                    const country = data.address.country || "";

                    // Only dispatch if meaningful
                    if (city || country) {
                        dispatch("locationSelect", {
                            city,
                            country,
                            lat,
                            lng,
                        });
                    }
                }
            } catch (e) {
                console.error("Geocoding failed", e);
            }
        }, 800);
    }
    /**
     * Centre la carte sur la position de l'utilisateur (Geolocation API).
     * Le navigateur demande l'autorisation ; l'appel doit être déclenché par
     * une action utilisateur, ce qui est le cas de ce bouton.
     */
    function locateUser() {
        if (!map || !marker || !leaflet || locating) return;

        if (!("geolocation" in navigator)) {
            dispatch("error", {
                message:
                    "La géolocalisation n'est pas disponible dans ce navigateur.",
            });
            return;
        }

        locating = true;
        try {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const latlng = leaflet.latLng(
                        position.coords.latitude,
                        position.coords.longitude,
                    );

                    isProgrammaticMove = true;
                    marker.setLatLng(latlng);
                    updatePreviewRectangle(latlng);
                    map.setView(latlng, 13);
                    lookupAddress(latlng.lat, latlng.lng, true);

                    setTimeout(() => {
                        isProgrammaticMove = false;
                    }, 1200);

                    locating = false;
                },
                (error) => {
                    locating = false;
                    let message =
                        "Impossible de récupérer votre position. Réessayez.";
                    if (error.code === 1) {
                        message =
                            "Localisation refusée. Autorisez l'accès à votre position dans le navigateur.";
                    } else if (error.code === 3) {
                        message =
                            "La localisation a expiré. Vérifiez votre connexion et réessayez.";
                    }
                    dispatch("error", { message });
                },
                {
                    enableHighAccuracy: false,
                    timeout: 10000,
                    maximumAge: 300000,
                },
            );
        } catch {
            locating = false;
            dispatch("error", {
                message:
                    "Impossible d'initialiser la géolocalisation dans ce navigateur.",
            });
        }
    }

    export function fitToPreview() {
        if (map && previewRect) {
            map.fitBounds(previewRect.getBounds(), { padding: [50, 50] });
        }
    }
</script>

<div class="map-shell">
    <div
        class="map-container"
        class:tiles-dark={tileTone === "dark"}
        class:tiles-light={tileTone === "light"}
        bind:this={mapElement}
    ></div>

    <div class="map-tools">
        <button
            type="button"
            class="map-tool"
            on:click={locateUser}
            disabled={locating}
            title="Centrer la carte sur ma position"
            aria-label="Centrer la carte sur ma position"
        >
            {#if locating}
                <span class="spinner" aria-hidden="true"></span>
            {:else}
                <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                    stroke-linecap="round"
                    aria-hidden="true"
                >
                    <circle cx="12" cy="12" r="3.5"></circle>
                    <path d="M12 2v3M12 19v3M2 12h3M19 12h3"></path>
                </svg>
            {/if}
            <span>{locating ? "Localisation…" : "Ma position"}</span>
        </button>
    </div>
</div>

<style>
    .map-shell {
        position: relative;
        width: 100%;
        height: 100%;
        min-height: 400px;
    }

    .map-container {
        width: 100%;
        height: 100%;
        min-height: 400px;
        border-radius: 0;
        border: none;
        margin: 0;
        z-index: 1;
    }

    .map-tools {
        position: absolute;
        top: 64px;
        right: 20px;
        z-index: 500;
    }

    .map-tool {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 9px 13px;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: rgba(10, 13, 18, 0.78);
        color: var(--text);
        backdrop-filter: blur(14px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.32);
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        transition:
            background 0.18s ease,
            border-color 0.18s ease,
            transform 0.18s ease;
    }

    .map-tool:hover:not(:disabled) {
        background: rgba(20, 26, 34, 0.94);
        border-color: rgba(103, 232, 249, 0.45);
        transform: translateY(-1px);
    }

    .map-tool:disabled {
        cursor: wait;
        opacity: 0.75;
    }

    .map-tool svg {
        width: 16px;
        height: 16px;
        color: var(--accent);
        flex: none;
    }

    .spinner {
        width: 14px;
        height: 14px;
        border: 2px solid rgba(255, 255, 255, 0.22);
        border-top-color: var(--accent);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        flex: none;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    /* Contrôles Leaflet au même langage visuel que le reste de l'app. */
    .map-shell :global(.leaflet-bar) {
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
    }

    .map-shell :global(.leaflet-bar a) {
        background: rgba(13, 17, 22, 0.9) !important;
        color: var(--text) !important;
        border-bottom-color: var(--border) !important;
    }

    .map-shell :global(.leaflet-bar a:hover) {
        background: var(--panel-2) !important;
        color: var(--accent) !important;
    }

    .map-shell :global(.leaflet-control-attribution) {
        background: rgba(10, 13, 18, 0.78) !important;
        color: var(--muted) !important;
        font-size: 10px;
        padding: 2px 7px;
        border-radius: 7px 0 0 0;
    }

    .map-shell :global(.leaflet-control-attribution a) {
        color: var(--accent) !important;
    }

    /* Aperçu sombre / clair sans fournisseur de tuiles payant. Le filtre ne
       s'applique qu'au calque des tuiles, pas au marqueur ni au rectangle. */
    .map-container :global(.leaflet-tile-pane) {
        transition: filter 0.2s ease;
    }

    .map-container.tiles-dark :global(.leaflet-tile-pane) {
        filter: grayscale(1) invert(1) brightness(0.85) contrast(1.15);
    }

    .map-container.tiles-light :global(.leaflet-tile-pane) {
        filter: grayscale(1) brightness(1.05) contrast(0.9);
    }

    @media (max-width: 768px) {
        .map-tools {
            top: calc(20px + env(safe-area-inset-top));
            right: calc(12px + env(safe-area-inset-right));
        }

        .map-tool {
            min-height: 44px;
        }

        .map-shell :global(.leaflet-control-zoom) {
            display: none;
        }

        .map-shell :global(.leaflet-bottom) {
            bottom: env(safe-area-inset-bottom);
        }
    }

    @media (max-width: 480px) {
        .map-tool {
            padding: 10px;
        }

        .map-tool span:last-child {
            display: none;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .spinner {
            animation: none;
        }
    }
</style>
