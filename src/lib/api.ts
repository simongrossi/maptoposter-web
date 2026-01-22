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

// Helper to parse SSE format roughly
export async function generatePoster(
    payload: GenerationRequest,
    onProgress?: (percent: number, text: string) => void,
    signal?: AbortSignal
): Promise<GenerationResponse> {
    try {
        const res = await fetch("/api/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal
        });

        if (!res.ok || !res.body) {
            return {
                success: false,
                files: [],
                error: `Erreur serveur: ${res.status} ${res.statusText}`
            };
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop() || ""; // Keep incomplete chunk

            for (const block of lines) {
                const eventMatch = block.match(/event: (.*)\n/);
                const dataMatch = block.match(/data: (.*)/);

                if (eventMatch && dataMatch) {
                    const type = eventMatch[1].trim();
                    const dataStr = dataMatch[1];
                    try {
                        const data = JSON.parse(dataStr);
                        if (type === "progress" && onProgress) {
                            onProgress(data.percent, data.text);
                        } else if (type === "result") {
                            return { success: true, files: data.files };
                        } else if (type === "error") {
                            return { success: false, files: [], error: data.message };
                        }
                    } catch (e) {
                        console.error("JSON parse error in SSE", e);
                    }
                }
            }
        }

        // If stream ends without result
        return { success: false, files: [], error: "Connexion interrompue sans résultat." };

    } catch (e: any) {
        if (e.name === 'AbortError') {
            return { success: false, files: [], error: "Génération annulée." };
        }
        return {
            success: false,
            files: [],
            error: "Erreur de communication avec le serveur: " + (e.message || "Unknown error")
        };
    }
}
