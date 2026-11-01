import { json, type RequestHandler } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export const POST: RequestHandler = async ({ request }) => {
    try {
        const body = await request.json();
        const {
            city,
            country,
            name,
            countryLabel,
            distance,
            theme,
            allThemes,
            customLayers,
            customColors,
            format,
            dpi,
            margins,
            paperSize,
            width,
            height,
        } = body ?? {};

        // Validation minimale : le backend applique la validation stricte.
        if (typeof city !== 'string' || typeof country !== 'string' || !city.trim() || !country.trim()) {
            return json({ error: 'Missing mandatory fields (city, country)' }, { status: 400 });
        }

        const API_URL = env.API_URL || 'http://localhost:8000';

        // Payload explicite : on ne relaie pas de champs arbitraires.
        const payload = {
            city: city.trim(),
            country: country.trim(),
            style: theme || 'feature_based',
            all_themes: Boolean(allThemes),
            distance: Number(distance) || 10000,
            width: Number(width) || 12.0,
            height: Number(height) || 16.0,
            country_label: countryLabel || undefined,
            name_label: name || undefined,
            custom_layers: Array.isArray(customLayers)
                ? customLayers.filter((layer: any) => layer && layer.enabled)
                : [],
            custom_colors: customColors || undefined,
            format: format || 'png',
            dpi: Number(dpi) || 300,
            margins: Number(margins) || 0,
            paper_size: paperSize || 'custom',
        };

        // Le cookie de session doit suivre la requete, sinon l'API cree une
        // nouvelle session cote serveur SvelteKit et l'ownership est perdu.
        const cookie = request.headers.get('cookie');
        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (cookie) headers.cookie = cookie;

        const response = await fetch(`${API_URL}/generate`, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload),
        });

        const text = await response.text();
        let data: any;
        try {
            data = text ? JSON.parse(text) : {};
        } catch {
            data = { error: 'Invalid backend response' };
        }

        const result = json(data, { status: response.status });
        const setCookie = response.headers.get('set-cookie');
        if (setCookie) {
            result.headers.append('set-cookie', setCookie);
        }
        return result;
    } catch (error: any) {
        console.error('Generate API error:', error);
        return json({ error: 'Internal Server Error' }, { status: 500 });
    }
};
