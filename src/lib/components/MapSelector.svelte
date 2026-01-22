<script lang="ts">
    import { onMount, createEventDispatcher } from "svelte";
    import { browser } from "$app/environment";

    export let initialDefaults = { lat: 48.8566, lng: 2.3522 }; // Paris default
    export let distance: number = 29000;

    const dispatch = createEventDispatcher();
    let mapElement: HTMLElement;
    let map: any;
    let circle: any;
    let marker: any;
    let L: any;

    onMount(async () => {
        if (browser) {
            // Dynamic import for SSR compatibility
            const module = await import("leaflet");
            L = module.default;
            await import("leaflet/dist/leaflet.css");

            initMap();
        }
    });

    $: if (map && distance) {
        updateCircleRadius();
    }

    function initMap() {
        if (!mapElement) return;

        // Create map
        map = L.map(mapElement).setView(
            [initialDefaults.lat, initialDefaults.lng],
            10,
        );

        // Tile layer (OSM)
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map);

        // Marker (draggable center)
        marker = L.marker([initialDefaults.lat, initialDefaults.lng], {
            draggable: true,
        }).addTo(map);

        // Circle (radius)
        circle = L.circle([initialDefaults.lat, initialDefaults.lng], {
            color: "#0070f3",
            fillColor: "#0070f3",
            fillOpacity: 0.2,
            radius: distance,
        }).addTo(map);

        // Events
        marker.on("dragend", handleMarkerDrag);
        map.on("click", (e: any) => {
            marker.setLatLng(e.latlng);
            handleMarkerDrag();
        });

        // Trigger initial lookup
        lookupAddress(initialDefaults.lat, initialDefaults.lng);
    }

    function updateCircleRadius() {
        if (circle) {
            circle.setRadius(distance);
        }
    }

    function handleMarkerDrag() {
        const latlng = marker.getLatLng();
        circle.setLatLng(latlng);
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
                const newLatLng = new L.LatLng(lat, lon);
                marker.setLatLng(newLatLng);
                circle.setLatLng(newLatLng);
                map.setView(newLatLng, 12); // slightly closer zoom for cities

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
