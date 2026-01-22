import { json, type RequestHandler } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export const POST: RequestHandler = async ({ request }) => {
    try {
        const body = await request.json();
        const { city, country, name, countryLabel, distance, theme, allThemes, customLayers, customColors, format } = body;

        // Validation
        if (!city || !country) {
            return json({ error: "Missing mandatory fields (city, country)" }, { status: 400 });
        }

        const API_URL = process.env.API_URL || "http://localhost:8000";

        // Prepare payload (Pydantic model)
        const payload = {
            city,
            country,
            style: theme || "feature_based",
            distance: distance || 10000,
            width: 12.0,
            height: 16.0,
            country_label: countryLabel,
            name_label: name,
            custom_layers: customLayers ? customLayers.filter((l: any) => l.enabled) : [],
            custom_colors: customColors,
            format: format || "png"
        };

        const response = await fetch(`${API_URL}/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`Erreur Backend (${response.status}): ${errText}`);
        }

        const data = await response.json();
        // data = { task_id: "..." }
        return json(data);

    } catch (error: any) {
        console.error("Generate API error:", error);
        return json({ error: error.message || "Internal Server Error" }, { status: 500 });
    }
};
