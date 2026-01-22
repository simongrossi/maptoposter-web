import { error, type RequestHandler } from '@sveltejs/kit';
import fs from 'fs';
import path from 'path';

export const GET: RequestHandler = async ({ params }) => {
    // Sanitize filename to prevent directory traversal, but allow unicode (accents)
    // We just ensure there are no directory separators
    const rawFilename = params.filename ?? '';
    const filename = path.basename(rawFilename);

    // Use env var for storage path, fallback to static/posters for local dev
    const storageDir = process.env.POSTERS_DIR || path.resolve('static/posters');
    const filePath = path.join(storageDir, filename);

    if (!fs.existsSync(filePath)) {
        throw error(404, 'Poster not found');
    }

    try {
        const file = fs.readFileSync(filePath);
        return new Response(file, {
            headers: {
                'Content-Type': 'image/png',
                'Content-Disposition': `inline; filename="${filename}"`
            }
        });
    } catch (e) {
        throw error(500, 'Error reading file');
    }
};
