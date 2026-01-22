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

export interface CustomLayer {
    label: string;
    tags: Record<string, string>;
    color: string;
    width?: number;
    enabled: boolean;
}

export interface GenerationRequest {
    city: string;
    country: string;
    distance: number;
    name?: string;
    countryLabel?: string;
    theme?: string;
    allThemes?: boolean;
    customLayers?: CustomLayer[];
    customColors?: {
        bg?: string;
        water?: string;
        parks?: string;
        roads?: string;
        text?: string;
    };
}

export interface GenerationResponse {
    success: boolean;
    files: string[];
    error?: string;
    debug?: string;
}
