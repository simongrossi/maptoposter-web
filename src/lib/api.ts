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

export async function generatePoster(payload: GenerationRequest): Promise<GenerationResponse> {
    try {
        const res = await fetch("/api/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const result: GenerationResponse = await res.json();
        return result;
    } catch (e: any) {
        return {
            success: false,
            files: [],
            error: "Erreur de communication avec le serveur: " + (e.message || "Unknown error")
        };
    }
}
