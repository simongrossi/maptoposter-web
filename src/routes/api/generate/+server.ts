import { json, type RequestHandler } from '@sveltejs/kit';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

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

        // Capture files before
        const postersDir = path.resolve('static/posters');
        if (!fs.existsSync(postersDir)) fs.mkdirSync(postersDir, { recursive: true });

        const filesBefore = fs.readdirSync(postersDir);

        return new Promise((resolve) => {
            // Try to get python path from env, or fallback
            // Note: In SvelteKit, process.env isn't always fully populated in dev without $env/dynamic/private
            // We'll try to use the one from .env if possible via a direct check or standard PATH resolution
            let pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

            // Hardcoded fallback for this specific user environment if needed, 
            // but ideally we rely on the process.env if loaded.
            // Since we can't easily import $env/dynamic/private dynamically in a replace block without adding imports atop,
            // we will stick to a robust check.

            // However, we just wrote a .env file. Vite loads it into process.env in dev mode usually.
            if (process.env.PYTHON_PATH) {
                pythonCmd = process.env.PYTHON_PATH;
            } else {
                // Extreme fallback for the specific user case found:
                if (fs.existsSync("C:\\Users\\simongrossi\\AppData\\Local\\Programs\\Python\\Python311\\python.exe")) {
                    pythonCmd = "C:\\Users\\simongrossi\\AppData\\Local\\Programs\\Python\\Python311\\python.exe";
                }
            }

            const processRef = spawn(pythonCmd, args, {
                cwd: process.cwd(),
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
            });

            let stderrData = '';

            processRef.stderr.on('data', (data: Buffer) => {
                stderrData += data.toString();
            });

            processRef.stdout.on('data', (data: Buffer) => {
                // Optional: log stdout
                console.log(data.toString());
            });

            processRef.on('close', (code: number) => {
                if (code !== 0) {
                    console.error("Python script error:", stderrData);
                    resolve(json({
                        success: false,
                        error: "Le script a échoué (code " + code + ").",
                        debug: stderrData || "Aucune sortie d'erreur (stderr est vide)."
                    }, { status: 500 }));
                    return;
                }

                const filesAfter = fs.readdirSync(postersDir);
                const newFiles = filesAfter.filter((f: string) => !filesBefore.includes(f));

                if (newFiles.length === 0) {
                    resolve(json({
                        success: false,
                        error: "Aucun fichier détecté après exécution.",
                        debug: "Sortie stderr: " + stderrData
                    })); // Not a 500, technically it ran but didn't produce files
                    return;
                }

                resolve(json({ success: true, files: newFiles }));
            });

            processRef.on('error', (err: Error) => {
                resolve(json({ success: false, error: "Failed to spawn process: " + err.message }, { status: 500 }));
            });
        });

    } catch (error) {
        console.error("API error:", error);
        return json({ error: "Internal Server Error" }, { status: 500 });
    }
};
