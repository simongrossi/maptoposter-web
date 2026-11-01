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

    function lookupAddress(lat: number, lng: number) {
        if (isProgrammaticMove) return;

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
    export function fitToPreview() {
        if (map && previewRect) {
            map.fitBounds(previewRect.getBounds(), { padding: [50, 50] });
        }
    }
</script>

<div
    class="map-container"
    class:tiles-dark={tileTone === "dark"}
    class:tiles-light={tileTone === "light"}
    bind:this={mapElement}
></div>

<style>
    .map-container {
        width: 100%;
        height: 100%;
        min-height: 400px;
        border-radius: 0;
        border: none;
        margin: 0;
        z-index: 1;
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
</style>
