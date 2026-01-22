import { json, type RequestHandler } from '@sveltejs/kit';

export const GET: RequestHandler = async ({ params }) => {
    try {
        const taskId = params.id;
        if (!taskId) return json({ error: "No task ID" }, { status: 400 });

        const API_URL = process.env.API_URL || "http://localhost:8000";

        const response = await fetch(`${API_URL}/tasks/${taskId}`);

        if (!response.ok) {
            return json({ error: "Failed to fetch task status" }, { status: response.status });
        }

        const data = await response.json();
        return json(data);

    } catch (error: any) {
        console.error("Task API Error:", error);
        return json({ error: "Internal Server Error" }, { status: 500 });
    }
};
