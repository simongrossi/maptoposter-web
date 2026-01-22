import { json, type RequestHandler } from '@sveltejs/kit';
import fs from 'fs';
import path from 'path';

export const GET: RequestHandler = async () => {
    try {
        const themesDir = path.resolve('themes');
        if (!fs.existsSync(themesDir)) {
            return json({ themes: [] });
        }

        const files = fs.readdirSync(themesDir);
        const themes = files
            .filter((file: string) => file.endsWith('.json'))
            .map((file: string) => {
                const content = fs.readFileSync(path.join(themesDir, file), 'utf-8');
                try {
                    const jsonContent = JSON.parse(content);
                    return {
                        id: file.replace('.json', ''),
                        name: jsonContent.name || file.replace('.json', ''),
                        colors: {
                            bg: jsonContent.bg,
                            road_primary: jsonContent.road_primary,
                            water: jsonContent.water
                        }
                    };
                } catch (e) {
                    return { id: file.replace('.json', ''), name: file.replace('.json', '') };
                }
            });

        return json({ themes });
    } catch (error) {
        console.error("Error reading themes:", error);
        return json({ error: "Failed to load themes" }, { status: 500 });
    }
};
