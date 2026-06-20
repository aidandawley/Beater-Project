# Beater Todo Lab

A deliberately janky, self-hosted Todo app for testing security tools. It uses:

- React + Vite frontend
- FastAPI backend
- SQLite SQL database
- Google OAuth sign-in
- Gemini 1.5 Flash powered side chatbot
- Docker Compose for Windows Docker Desktop + Ubuntu/WSL workflows

> ⚠️ **Security lab notice:** this project intentionally includes several marked vulnerabilities so scanners and review tools have something to find. Do not deploy it to the public internet.

## Quick start on Windows with Docker Desktop + Ubuntu/WSL

Open Ubuntu/WSL in the project folder and run:

```bash
cp .env.example .env
# edit .env and fill in GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GEMINI_API_KEY

docker compose up --build
```

Then open:

- Frontend: <http://localhost:5173>
- Backend docs: <http://localhost:8000/docs>

## Google OAuth setup

1. Go to Google Cloud Console > APIs & Services > Credentials.
2. Create an OAuth 2.0 Client ID for a Web application.
3. Add this authorized redirect URI:
   - `http://localhost:8000/auth/google/callback`
4. Put the generated values in `.env`:
   - `GOOGLE_CLIENT_ID=...`
   - `GOOGLE_CLIENT_SECRET=...`

## Google sign-in troubleshooting

If sign-in returns a Google `400 redirect_uri_mismatch`, make sure the OAuth client has this exact redirect URI, including `http` and port:

- `http://localhost:8000/auth/google/callback`

Also make sure `BACKEND_URL=http://localhost:8000` has no different hostname, trailing path, or HTTPS scheme while running the local Docker setup. The backend builds the Google authorization and token-exchange redirect URI from `BACKEND_URL`.

## Gemini setup

1. Create a Gemini API key in Google AI Studio.
2. Put it in `.env` as `GEMINI_API_KEY=...`.
3. The backend uses `gemini-1.5-flash` in `backend/app/gemini_client.py`.

## Resource allocation guide for Docker Desktop on Windows

For a small personal lab:

1. Open Docker Desktop.
2. Go to **Settings > Resources**.
3. Suggested allocation:
   - CPUs: 2
   - Memory: 4 GB
   - Swap: 1 GB
   - Disk image: at least 20 GB free
4. If using WSL integration, enable your Ubuntu distro in **Settings > Resources > WSL integration**.
5. Restart Docker Desktop after changing resources.

If the frontend install feels slow, increase memory to 6-8 GB temporarily while building images.

## Development commands

```bash
# Backend locally
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend locally
cd frontend
npm install
npm run dev -- --host 0.0.0.0

# Docker
cd ..
docker compose up --build
```

## Deliberately marked vulnerabilities

Search for `SECURITY_TEST_VULN` in the code. The app contains intentionally weak patterns, including:

- loose session cookie settings for local testing
- missing ownership enforcement on one todo read path
- partial input validation gaps in one update route
- verbose auth error handling
- unescaped chatbot rendering on the frontend

These are intentional for scanner validation and should be fixed before using the app for anything real.

## Deployment note

This repo is meant to simulate a first-time Windows-hosted Docker deployment running Linux containers through Docker Desktop/WSL. Keep it bound to localhost unless you are running it in an isolated security lab network.
