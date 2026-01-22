export interface Theme {
    id: string;
    name: string;
    colors?: {
        bg?: string;
        road_primary?: string;
        water?: string;
    };
    description?: string;
}

export interface GenerationRequest {
    city: string;
    country: string;
    distance: number;
    name?: string;
    countryLabel?: string;
    theme?: string;
    allThemes?: boolean;
}

export interface GenerationResponse {
    success: boolean;
    files: string[];
    error?: string;
    debug?: string;
}
