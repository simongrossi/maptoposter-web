import { json, type RequestHandler } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

const TASK_ID_RE = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

export const GET: RequestHandler = async ({ params, request }) => {
    try {
        const taskId = params.id;
        if (!taskId || !TASK_ID_RE.test(taskId)) {
            return json({ error: 'No task ID' }, { status: 400 });
        }

        const API_URL = env.API_URL || 'http://localhost:8000';
        const cookie = request.headers.get('cookie');
        const headers: Record<string, string> = {};
        if (cookie) headers.cookie = cookie;

        const response = await fetch(`${API_URL}/tasks/${taskId}`, { headers });
        const text = await response.text();
        let data: any;
        try {
            data = text ? JSON.parse(text) : {};
        } catch {
            data = { error: 'Invalid backend response' };
        }

        const result = json(data, { status: response.status });
        const setCookie = response.headers.get('set-cookie');
        if (setCookie) {
            result.headers.append('set-cookie', setCookie);
        }
        return result;
    } catch (error: any) {
        console.error('Task API Error:', error);
        return json({ error: 'Internal Server Error' }, { status: 500 });
    }
};
