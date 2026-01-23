# MapPoster Web v2.0 🌍🎨

**Turn any location into a stunning minimalist wall art poster.**

MapPoster is a modern, microservices-based web application that generates high-resolution map posters using OpenStreetMap data. It features a rich SvelteKit frontend and a robust Python/FastAPI backend powered by Celery execution.

![Preview](static/preview.png)

---

## ✨ Features

- **Global Search**: Find any city, village, or landmark worldwide.
- **WYSIWYG Preview**: Interactive map with real-time vector tile preview matching your theme (Dark/Light).
- **Artistic Themes**: Pre-defined styles (Noir, Minimal, Blueprint, Sunset) + **Custom Colors** dashboard.
- **High Resolution**: Exports print-ready PNG, SVG, or PDF files.
- **Custom Layers**: Toggle extra details (Cycle paths, Subways, Railways, Rivers).
- **Mobile Friendly**: Fully responsive design with drawer controls on mobile.
- **Microservices Architecture**: Industrial-grade setup with Redis, Celery, and S3 storage.

---

## 🏗️ Architecture

The project follows a cloud-native **Antigravity** architecture:

```mermaid
graph TD
    Client[Browser (SvelteKit)] -->|HTTP/443| Nginx[Nginx Gateway]
    Nginx -->|/api| API[FastAPI (Dispatcher)]
    Nginx -->|/| Frontend[Node.js (SSR)]
    
    API -->|Enqueue Task| Redis[(Redis Broker)]
    Worker -->|Fetch Task| Redis
    
    Worker[Celery Worker (Python)] -->|Fetch GeoData| OSM[OpenStreetMap API]
    Worker -->|Upload Poster| MinIO[(MinIO / S3 Storage)]
    
    Client -->|Poll Status| API
    API -->|Get Status| Redis
    Client -->|Download| MinIO
```

- **Frontend**: SvelteKit + TypeScript. Mobile-first, component-based.
- **API**: FastAPI (Python 3.11). Lightweight dispatcher.
- **Worker**: Celery + OSMnx + Matplotlib. Stateless, heavy-lifting.
- **Storage**: MinIO (S3 compatible). Cloud-native file handling.
- **Queue**: Redis.
- **Gateway**: Nginx. Handles security headers, routing, and caching.

---

## 🚀 Getting Started

The only requirement is **Docker** and **Docker Compose**.

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/maptoposter-web.git
   cd maptoposter-web
   ```

2. **Launch the stack**
   ```bash
   docker-compose up --build
   ```
   *Wait a few minutes for the initial build and Python dependency installation.*

3. **Access the App**
   - Application: **[http://localhost](http://localhost)**
   - MinIO Console: [http://localhost:9001](http://localhost:9001) (User: `minioadmin` / Pass: `minioadminpassword`)

---

## 🧪 Testing & Quality

To run the test suite locally:

**Backend Tests**
```bash
# Requires python + pip installed locally
pip install -r requirements.txt
pytest
```

**Frontend Tests**
```bash
npm install
npm run test:unit  # Vitest
npx playwright test # E2E
```

---

## 🛡️ Security & Performance

- **Rate Limiting**: API is protected (5 requests/min per IP) to prevent abuse.
- **Caching**: 
  - **Result Cache**: Identical requests (same city + style + options) return instantly via S3 hash verification.
  - **Tile Cache**: Frontend caching via standard browser mechanisms.
- **Observability**: **Sentry** integration ready (provide `SENTRY_DSN` in env).

---

## 📜 License

MIT License.
Data © OpenStreetMap contributors.
Map tiles © CartoDB & OpenStreetMap.
