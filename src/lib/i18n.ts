export const t = {
    errors: {
        locationNotFound: "Lieu introuvable sur OpenStreetMap.",
        geocodingError: "Erreur lors de la recherche du lieu.",
        cityRequired: "Veuillez entrer une ville.",
        countryRequired: "Veuillez entrer un pays.",
        serverError: "Erreur serveur : ",
        unknownError: "Une erreur inconnue est survenue.",
        generationCancelled: "Génération annulée."
    },
    status: {
        decoding: "Analyse des paramètres...",
        fetching: "Téléchargement des données OSM...",
        rendering: "Rendu de la carte...",
        uploading: "Envoi vers le cloud...",
        success: "Terminé !",
        restored: "Restauré depuis le cache."
    }
};

export function getStatusLabel(backendStatus: string): string {
    const s = backendStatus.toLowerCase();
    if (s.includes("decoding")) return t.status.decoding;
    if (s.includes("fetching")) return t.status.fetching;
    if (s.includes("rendering")) return t.status.rendering;
    if (s.includes("uploading")) return t.status.uploading;
    if (s.includes("restored")) return t.status.restored;
    return backendStatus; // Fallback
}
