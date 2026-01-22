import { json, type RequestHandler } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export const POST: RequestHandler = async ({ request }) => {
    try {
        const body = await request.json();
        const { city, country, name, countryLabel, distance, theme, allThemes, customLayers } = body;

        // Validation
        if (!city || !country) {
            return json({ error: "Missing mandatory fields (city, country)" }, { status: 400 });
        }

        // Determine API URL (Docker or Local)
        // In Docker, 'api' is the hostname. Local fallback 'localhost'.
        const API_URL = process.env.API_URL || "http://localhost:8000";

        // Prepare payload for FastAPI
        const payload = {
            city,
            country,
            style: theme || "feature_based", // FastAPI uses 'style'
            distance: distance || 10000,
            width: 12.0,
            height: 16.0,
            country_label: countryLabel,
            name_label: name,
            custom_layers: customLayers ? customLayers.filter((l: any) => l.enabled) : [],
            format: "png"
        };


        // --- SSE STREAMING RESPONSE ---
        const encoder = new TextEncoder();

        const stream = new ReadableStream({
            async start(controller) {
                function sendEvent(type: string, data: any) {
                    const msg = `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;
                    controller.enqueue(encoder.encode(msg));
                }

                try {
                    sendEvent("progress", { percent: 10, text: "Envoi de la demande au serveur..." });

                    // Call Python API
                    // Note: This is an await call, so we won't get granular progress from Python 
                    // unless we implement streaming on Python side too. 
                    // For now, we simulate "Working" state.
                    const response = await fetch(`${API_URL}/generate`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                    });

                    if (!response.ok) {
                        const errText = await response.text();
                        throw new Error(`Erreur API Python (${response.status}): ${errText}`);
                    }

                    const result = await response.json();

                    if (result.success) {
                        // Extract filename from URL or path
                        // result.file_url might be /posters/filename.png
                        // The frontend expects just the filename in a list
                        const filename = result.file_url.split('/').pop();

                        sendEvent("progress", { percent: 100, text: "Génération terminée !" });
                        sendEvent("result", { files: [filename] });
                    } else {
                        throw new Error("L'API a retourné une erreur sans détails.");
                    }

                } catch (err: any) {
                    console.error("Generate Proxy Error:", err);
                    sendEvent("error", { message: err.message || "Erreur de communication avec le moteur de génération." });
                } finally {
                    controller.close();
                }
            }
        });

        return new Response(stream, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        });

    } catch (error) {
        console.error("API Route error:", error);
        return json({ error: "Internal Server Error" }, { status: 500 });
    }
};
