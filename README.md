# Kerf

A web app that turns 3D furniture models into cut lists, shopping lists, and cost estimates. Upload a 3MF file, pick your materials, and get a complete bill of materials priced against real lumber supplier catalogs.

## What It Does

1. **Upload** a 3MF file (units built in) from any CAD tool
2. **Analyze** — extracts individual parts, classifies them as solid lumber or sheet goods based on geometry, maps to standard lumber sizes with milling allowances
3. **Price** — scrapes current prices from Woodworkers Source, shows cost estimates with direct links to product pages
4. **Export** — download a PDF project plan with 3D model thumbnail, parts list, shopping list, cut pieces, and cost breakdown

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | SvelteKit, TypeScript, Tailwind CSS, Three.js |
| Backend | Python, FastAPI, NumPy, BeautifulSoup4 |
| PDF | WeasyPrint, Jinja2 |
| 3D Viewer | Three.js + 3MFLoader + OrbitControls |
| Deployment | Docker Compose |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 22+
- WeasyPrint system libraries (see below)

### WeasyPrint System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info
```

**macOS:**
```bash
brew install pango libffi
```

### Development

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Docker Compose

```bash
docker compose up --build
```

Frontend at http://localhost:3000, backend at http://localhost:8000.

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest -v
```

115 tests covering: 3MF parsing, geometry analysis, material mapping, supplier pricing, API endpoints, and PDF report generation.

## Project Structure

```
kerf/
├── backend/                  # Python FastAPI
│   ├── app/
│   │   ├── main.py           # API routes
│   │   ├── models.py         # Pydantic models
│   │   ├── parser/           # 3MF file parsing
│   │   ├── analyzer/         # Geometry analysis, board classification
│   │   ├── mapper/           # Material mapping, cut list generation
│   │   ├── suppliers/        # Supplier pricing (scraper + static fallback)
│   │   ├── report.py         # PDF generation
│   │   └── templates/        # Jinja2 report template
│   └── tests/
├── frontend/                 # SvelteKit
│   └── src/
│       ├── lib/components/   # Upload, ModelViewer, Configure, Results
│       └── routes/           # Main page
└── docker-compose.yml
```

## How It Works

### 3MF Parsing

3MF files are ZIP archives containing XML mesh data with built-in units. The parser extracts individual bodies, applies build transforms, and converts all dimensions to millimeters internally.

### Board Classification

Parts are classified by geometry using priority rules:
1. Thickness > 1.5" -> thick stock (may need lamination)
2. Thin + wide + large area -> sheet good (plywood)
3. Width > 12" -> solid lumber with glue-up
4. Otherwise -> solid lumber

### Material Mapping

- Thickness snapped to nearest standard (4/4, 5/4, 6/4, 8/4)
- Milling allowances added (+1/4" thickness, +1/2" width, +1" length)
- Board feet calculated for solid lumber
- Sheet count calculated for plywood (naive area method)

### Pricing

Live prices scraped from Woodworkers Source with a 24-hour JSON cache. Falls back to static baseline prices if scraping fails. The supplier interface is modular for adding other sources.

## License

MIT
