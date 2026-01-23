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
    tags: Record<string, any>;
    color: string;
    width?: number;
    enabled: boolean;
}

export interface GenerationRequest {
    city: string;
    country: string;
    distance: number;
    format?: string;
    name_label?: string;
    country_label?: string;
    style?: string;
    all_themes?: boolean;
    custom_layers?: CustomLayer[];
    custom_colors?: {
        bg?: string;
        water?: string;
        parks?: string;
        roads?: string;
        text?: string;
    };
    dpi?: number;
    margins?: number;
    paper_size?: string;
    width?: number;
    height?: number;
}

export interface GenerationResponse {
    success: boolean;
    files: string[];
    error?: string;
    debug?: string;
}

export interface Preset {
    id: string;
    name: string;
    createdAt: number;
    data: {
        city: string;
        country: string;
        cityLabel: string;
        countryLabel: string;
        distance: number;
        selectedTheme: string;
        allThemes: boolean;
        customLayers: CustomLayer[];
        customColorsEnabled: boolean;
        customColors: any;
        exportFormat: string;
        dpi: number;
        margins: number;
        paperSize: string;
        width: number;
        height: number;
    };
}
