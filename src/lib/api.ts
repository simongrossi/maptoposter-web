import type { GenerationRequest, GenerationResponse, Theme } from './types';

export async function fetchThemes(): Promise<Theme[]> {
    try {
        const res = await fetch("/api/themes");
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const data = await res.json();
        return data.themes || [];
    } catch (e) {
        console.error("Failed to fetch themes", e);
        return [];
    }
}

export async function fetchHistory(limit = 10): Promise<any[]> {
    try {
        const res = await fetch(`/api/history?limit=${limit}`);
        if (!res.ok) return [];
        return await res.json();
    } catch (e) {
        console.error("Failed to fetch history", e);
        return [];
    }
}

// Helper for Polling Architecture
export async function generatePoster(
    payload: GenerationRequest,
    onProgress?: (percent: number, text: string) => void,
    signal?: AbortSignal
): Promise<GenerationResponse> {
    try {
        // 1. Submit JSON Task
        const res = await fetch("/api/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal
        });

        if (!res.ok) {
            const fallback = `Erreur serveur: ${res.status} ${res.statusText}`;
            let detail = "";
            try {
                const data = await res.json();
                detail = data?.detail || data?.message || "";
            } catch {
                detail = "";
            }
            if (res.status === 429) {
                return {
                    success: false,
                    files: [],
                    error: "Quota atteint. Veuillez réessayer dans quelques minutes."
                };
            }
            if (res.status === 422) {
                return {
                    success: false,
                    files: [],
                    error: "Paramètres invalides. Vérifiez la taille, la distance et le format."
                };
            }
            return {
                success: false,
                files: [],
                error: detail ? `${fallback} — ${detail}` : fallback
            };
        }

        const { task_id } = await res.json();

        if (!task_id) {
            return { success: false, files: [], error: "Pas de Task ID reçu." };
        }

        // 2. Poll Status
        while (true) {
            // Check abort signal
            if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');

            await new Promise(r => setTimeout(r, 1000)); // Wait 1s

            const statusRes = await fetch(`/api/tasks/${task_id}`, { signal });
            if (!statusRes.ok) continue; // Retry polling on glitch? or fail? Let's continue.

            const task = await statusRes.json();

            if (task.status === 'PROGRESS' || task.status === 'PENDING') {
                if (onProgress && task.progress) {
                    onProgress(task.progress.current || 0, task.progress.status || "Traitement...");
                }
            } else if (task.status === 'SUCCESS') {
                // Success!
                if (onProgress) onProgress(100, "Terminé !");
                // The result from celery task (tasks.py) contains { success: true, file_url: ... }
                // Frontend expects { success, files: [] } or something.
                // My tasks.py returns { success, file_url, ... }
                // Let's adapt it.
                const result = task.result;
                return {
                    success: true,
                    files: result.file_url ? [result.file_url] : [], // Use full URL from S3
                    debug: JSON.stringify(result)
                };
            } else if (task.status === 'FAILURE') {
                const rawError = task.error || "Erreur inconnue";
                let message = rawError;
                if (typeof rawError === "string") {
                    if (rawError.includes("No map data found") || rawError.includes("Could not retrieve map data")) {
                        message = "Aucune donnée OSM disponible pour cette zone. Essayez une distance plus petite.";
                    } else if (rawError.includes("Nominatim")) {
                        message = "Le service de géocodage est temporairement indisponible. Réessayez plus tard.";
                    }
                }
                return { success: false, files: [], error: message };
            }
        }

    } catch (e: any) {
        if (e.name === 'AbortError') {
            return { success: false, files: [], error: "Génération annulée." };
        }
        return {
            success: false,
            files: [],
            error: "Erreur de communication: " + (e.message || "Unknown error")
        };
    }
}
