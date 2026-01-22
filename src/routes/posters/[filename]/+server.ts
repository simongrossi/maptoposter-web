import { error, type RequestHandler } from '@sveltejs/kit';
import fs from 'fs';
import path from 'path';

export const GET: RequestHandler = async ({ params }) => {
    // Sanitize filename to prevent directory traversal
    const filename = (params.filename ?? '').replace(/[^a-zA-Z0-9_.-]/g, '');
    const filePath = path.resolve('static/posters', filename);

    if (!fs.existsSync(filePath)) {
        throw error(404, 'Poster not found');
    }

    try {
        const file = fs.readFileSync(filePath);
        return new Response(file, {
            headers: {
                'Content-Type': 'image/png',
                'Content-Disposition': `attachment; filename="${filename}"`
            }
        });
    } catch (e) {
        throw error(500, 'Error reading file');
    }
};
