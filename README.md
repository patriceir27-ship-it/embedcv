# EmbedCV Workshop Platform

AI-Assisted Code Generation for Embedded Systems with Computer Vision Applications

## Features
- User registration & JWT authentication
- Project management (CRUD)
- AI code generation for C, C++, Python, MicroPython, Arduino
- Hardware-aware profiling: RAM, Flash, Energy, Time Complexity
- Generation history with full metrics table
- Real-World Lab Workshop simulator
- PostgreSQL database (SQLite for local dev)

## Project Structure
```
embedcv/
├── backend/
│   ├── main.py          # FastAPI app + all routes
│   ├── database.py      # SQLAlchemy engine + session
│   ├── models.py        # DB models (User, Project, CodeGeneration)
│   ├── schemas.py       # Pydantic schemas
│   ├── static_serve.py  # Frontend file serving
│   └── requirements.txt
├── frontend/
│   └── index.html       # Full single-page app
├── render.yaml          # Render deployment config
├── Procfile
└── requirements.txt
```

## Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the backend (SQLite used by default locally)
cd backend
uvicorn main:app --reload --port 8000

# 3. Open frontend
open ../frontend/index.html
# OR visit http://localhost:8000 (served by FastAPI)
```

## Deploy to Render

### Option A — One-click with render.yaml (recommended)
1. Push this repo to GitHub
2. Go to https://render.com → New → Blueprint
3. Connect your GitHub repo
4. Render auto-reads `render.yaml` and creates the web service + PostgreSQL database
5. Done ✅

### Option B — Manual
1. Go to https://render.com → New Web Service
2. Connect your GitHub repo
3. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `DATABASE_URL` → your Render PostgreSQL connection string
   - `SECRET_KEY` → any long random string
5. Create a PostgreSQL database in Render and link it

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `sqlite:///./embedcv.db` |
| `SECRET_KEY` | JWT signing secret | `embedcv-super-secret-key-2025` |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login → JWT token |
| GET | `/auth/me` | Current user info |
| GET | `/projects` | List user projects |
| POST | `/projects` | Create project |
| DELETE | `/projects/{id}` | Delete project |
| POST | `/generate` | Generate code + profiling |
| GET | `/projects/{id}/generations` | Generation history |
| GET | `/stats` | Dashboard statistics |
| GET | `/health` | Health check |

## Next Steps (Thesis Implementation)
1. Replace `_simulate_code_generation()` in `main.py` with real LLM API call
2. Add actual cross-compilation with `arm-none-eabi-gcc` via subprocess
3. Add real binary analysis with `objdump` + `nm`
4. Fine-tune CodeLlama on embedded CV corpus
5. Add WebSocket for real-time lab monitoring
