<script lang="ts">
    import { onMount, createEventDispatcher } from "svelte";
    import { browser } from "$app/environment";
    import type * as L from "leaflet"; // Import definitions

    export let initialDefaults = { lat: 48.8566, lng: 2.3522 }; // Paris default
    export let distance: number = 10000;

    const dispatch = createEventDispatcher();
    let mapElement: HTMLElement;

    // Leaflet instances with types
    let map: L.Map;
    let previewRect: L.Rectangle;
    let marker: L.Marker;
    let leaflet: typeof L; // Runtime library

    // Poster config mirroring backend default (12x16 inch = 0.75 aspect)
    const ASPECT_RATIO = 12 / 16;

    onMount(async () => {
        if (browser) {
            // Dynamic import for SSR compatibility
            const module = await import("leaflet");
            leaflet = module.default; // use default export or module depending on setup
            // Note: sometimes module IS 'L', sometimes module.default. Vite/SvelteKit behavior.
            // Usually module.default is safe for ESM.

            await import("leaflet/dist/leaflet.css");

            initMap();
        }
    });

    $: if (map && distance && previewRect && marker) {
        updatePreviewRectangle(marker.getLatLng());
    }

    function initMap() {
        if (!mapElement) return;

        // Fix 404 on marker icons by resetting default icon options
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

        // Tile layer (OSM)
        leaflet
            .tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                attribution:
                    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            })
            .addTo(map);

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
            const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`;
            const res = await fetch(url, {
                headers: { "User-Agent": "MapToPosterClient/1.0" },
            });
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
            }
        } catch (e) {
            console.error("Forward geocoding failed", e);
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
</script>

<div class="map-container" bind:this={mapElement}></div>

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
</style>
