import { json, type RequestHandler } from '@sveltejs/kit';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { env } from '$env/dynamic/private';

export const POST: RequestHandler = async ({ request }) => {
    try {
        const body = await request.json();
        const { city, country, name, countryLabel, distance, theme, allThemes } = body;

        if (!city || !country) {
            return json({ error: "Missing mandatory fields (city, country)" }, { status: 400 });
        }

        const args = [
            'create_map_poster.py',
            '--city', city,
            '--country', country,
            '--distance', String(distance || 29000)
        ];

        if (allThemes) {
            args.push('--all-themes');
        } else {
            if (!theme) return json({ error: "Theme is required when allThemes is false" }, { status: 400 });
            args.push('--theme', theme);
        }

        if (name) {
            args.push('--name', name);
        }
        if (countryLabel) {
            args.push('--country-label', countryLabel);
        }

        // Handle Custom Layers
        if (body.customLayers && Array.isArray(body.customLayers)) {
            const activeLayers = body.customLayers.filter((l: any) => l.enabled);
            if (activeLayers.length > 0) {
                args.push('--custom-layers', JSON.stringify(activeLayers));
            }
        }

        // Ensure output directory exists
        const postersDir = path.resolve('static/posters');
        if (!fs.existsSync(postersDir)) fs.mkdirSync(postersDir, { recursive: true });

        return new Promise((resolve) => {
            // Determine Python executable
            // Priority: Env var -> python (win) -> python3 (unix)
            // Use SvelteKit's dynamic env access
            let pythonCmd = env.PYTHON_PATH;
            if (!pythonCmd) {
                pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
            }

            const processRef = spawn(pythonCmd, args, {
                cwd: process.cwd(),
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
            });

            let stdoutData = '';
            let stderrData = '';

            processRef.stdout.on('data', (data: Buffer) => {
                const str = data.toString();
                stdoutData += str;
                console.log(str); // Log for server debugging
            });

            processRef.stderr.on('data', (data: Buffer) => {
                stderrData += data.toString();
            });

            processRef.on('close', (code: number) => {
                if (code !== 0) {
                    console.error("Python script error:", stderrData);
                    resolve(json({
                        success: false,
                        error: "Le script a échoué (code " + code + ").",
                        debug: stderrData || "Aucune sortie d'erreur."
                    }, { status: 500 }));
                    return;
                }

                // Parse output for filenames
                // Robust parsing: Find the last occurrence of the marker and parse everything after it
                const marker = "__JSON_RESULT_FILES__:";
                const markerIndex = stdoutData.lastIndexOf(marker);
                let newFiles: string[] = [];

                if (markerIndex !== -1) {
                    const jsonStr = stdoutData.substring(markerIndex + marker.length).trim();
                    console.log("Parsing JSON from Python:", jsonStr); // Debug log
                    try {
                        newFiles = JSON.parse(jsonStr);
                    } catch (e) {
                        console.error("Failed to parse JSON result:", e);
                        console.error("String was:", jsonStr);
                    }
                } else {
                    console.error("Marker not found in stdout");
                }

                if (newFiles.length === 0) {
                    // Fallback or error if no files reported
                    resolve(json({
                        success: false,
                        error: "Aucun fichier généré n'a été détecté.",
                        debug: "Le script a terminé sans signaler de fichiers.\nSortie:\n" + stdoutData
                    }));
                    return;
                }

                resolve(json({ success: true, files: newFiles }));
            });

            processRef.on('error', (err: Error) => {
                resolve(json({ success: false, error: "Impossible de lancer le processus Python: " + err.message }, { status: 500 }));
            });
        });

    } catch (error) {
        console.error("API error:", error);
        return json({ error: "Internal Server Error" }, { status: 500 });
    }
};
