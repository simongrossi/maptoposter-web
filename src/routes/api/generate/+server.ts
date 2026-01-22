import { json, type RequestHandler } from '@sveltejs/kit';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { env } from '$env/dynamic/private';

export const POST: RequestHandler = async ({ request }) => {
    try {
        const body = await request.json();
        const { city, country, name, countryLabel, distance, theme, allThemes, customLayers } = body;

        if (!city || !country) {
            return json({ error: "Missing mandatory fields (city, country)" }, { status: 400 });
        }

        const args = [
            'create_map_poster.py',
            '--city', city,
            '--country', country,
            '--distance', String(distance || 10000)
        ];

        if (allThemes) {
            args.push('--all-themes');
        } else {
            if (!theme) return json({ error: "Theme is required when allThemes is false" }, { status: 400 });
            args.push('--theme', theme);
        }

        if (name) args.push('--name', name);
        if (countryLabel) args.push('--country-label', countryLabel);

        if (customLayers && Array.isArray(customLayers)) {
            const activeLayers = customLayers.filter((l: any) => l.enabled);
            if (activeLayers.length > 0) {
                args.push('--custom-layers', JSON.stringify(activeLayers));
            }
        }

        const postersDir = path.resolve('static/posters');
        if (!fs.existsSync(postersDir)) fs.mkdirSync(postersDir, { recursive: true });

        // Determine Python executable
        let pythonCmd = env.PYTHON_PATH;
        if (!pythonCmd) {
            pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
        }

        // --- STREAMING SETUP ---
        const encoder = new TextEncoder();

        const stream = new ReadableStream({
            start(controller) {
                const processRef = spawn(pythonCmd, args, {
                    cwd: process.cwd(),
                    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' }
                });

                // Kill process if client disconnects
                request.signal.addEventListener('abort', () => {
                    console.log("Client aborted, killing python process...");
                    processRef.kill();
                });

                function sendEvent(type: string, data: any) {
                    const msg = `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;
                    controller.enqueue(encoder.encode(msg));
                }

                let stdoutBuffer = '';

                processRef.stdout.on('data', (data: Buffer) => {
                    const str = data.toString();
                    stdoutBuffer += str;
                    console.log("[PY]", str.trim());

                    // Simple heuristic progress updates based on keywords
                    // We can refine this by parsing specific lines
                    const lower = str.toLowerCase();
                    if (lower.includes("fetching map data")) sendEvent("progress", { percent: 10, text: "Initialisation..." });
                    else if (lower.includes("street network")) sendEvent("progress", { percent: 20, text: "Téléchargement des routes..." });
                    else if (lower.includes("water features")) sendEvent("progress", { percent: 40, text: "Téléchargement de la géographie..." });
                    else if (lower.includes("parks")) sendEvent("progress", { percent: 50, text: "Ajout des parcs..." });
                    else if (lower.includes("rendering map")) sendEvent("progress", { percent: 70, text: "Rendu graphique en cours..." });
                    else if (lower.includes("hierarchy colors")) sendEvent("progress", { percent: 80, text: "Application du style..." });
                    else if (lower.includes("saving to")) sendEvent("progress", { percent: 95, text: "Sauvegarde du fichier..." });
                });

                let stderrData = '';
                processRef.stderr.on('data', (d) => stderrData += d.toString());

                processRef.on('close', (code) => {
                    if (code !== 0) {
                        // Check if it was killed by us (signal?) - usually code null or signal SIGTERM
                        // If standard error:
                        sendEvent("error", { message: "Erreur script: " + stderrData });
                        controller.close();
                        return;
                    }

                    // Parse the JSON result from the FULL buffer at the end
                    const marker = "__JSON_RESULT_FILES__:";
                    const markerIndex = stdoutBuffer.lastIndexOf(marker);

                    if (markerIndex !== -1) {
                        try {
                            const jsonStr = stdoutBuffer.substring(markerIndex + marker.length).trim();
                            const files = JSON.parse(jsonStr);
                            sendEvent("result", { files });
                        } catch (e) {
                            sendEvent("error", { message: "Erreur parsing JSON sortie Python" });
                        }
                    } else {
                        // Sometimes buffer issues, assume success if file exists? 
                        // No, let's report error if no marker found.
                        sendEvent("error", { message: "Pas de résultat retourné par le script." });
                    }

                    controller.close();
                });

                processRef.on('error', (err) => {
                    sendEvent("error", { message: "Spawn error: " + err.message });
                    controller.close();
                });
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
        console.error("API error:", error);
        return json({ error: "Internal Server Error" }, { status: 500 });
    }
};
