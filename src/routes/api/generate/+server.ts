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
                const match = stdoutData.match(/__JSON_RESULT_FILES__:(.*)/);
                let newFiles: string[] = [];

                if (match && match[1]) {
                    try {
                        newFiles = JSON.parse(match[1]);
                    } catch (e) {
                        console.error("Failed to parse JSON result from python script");
                    }
                }

                if (newFiles.length === 0) {
                    // Fallback or error if no files reported
                    resolve(json({
                        success: false,
                        error: "Aucun fichier généré n'a été signalé par le script.",
                        debug: "Sortie stdout: " + stdoutData
                    }));
                    return;
                }

                resolve(json({ success: true, files: newFiles }));
            });

            processRef.on('error', (err: Error) => {
                resolve(json({ success: false, error: "Impossible de lancer le processus Python: " + err.message + ". Vérifiez que Python est installé et accessible." }, { status: 500 }));
            });
        });

    } catch (error) {
        console.error("API error:", error);
        return json({ error: "Internal Server Error" }, { status: 500 });
    }
};
