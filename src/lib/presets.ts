import type { Preset } from './types';

const STORAGE_KEY = 'maptoposter_presets';

export function getPresets(): Preset[] {
    if (typeof localStorage === 'undefined') return [];
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        console.warn('Failed to load presets', e);
        return [];
    }
}

export function savePreset(preset: Preset): void {
    if (typeof localStorage === 'undefined') return;
    try {
        const list = getPresets();
        list.push(preset);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch (e) {
        console.error('Failed to save preset', e);
    }
}

export function deletePreset(id: string): void {
    if (typeof localStorage === 'undefined') return;
    try {
        let list = getPresets();
        list = list.filter(p => p.id !== id);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch (e) {
        console.error('Failed to delete preset', e);
    }
}
