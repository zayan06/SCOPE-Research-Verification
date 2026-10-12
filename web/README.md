# SCOPE web client

React, TypeScript, Vite, and Tailwind CSS frontend for the SCOPE research workspace.

## Run locally

From this directory:

```sh
npm install
npm run dev
```

Open the URL printed by Vite (normally http://127.0.0.1:5173). The default
workspace is labeled **Demo workspace** and uses synthetic sample records.

To connect to the local FastAPI backend, start it from the repository root in
a separate terminal:

```sh
uvicorn api.main:app --reload
```

Then switch **WORKSPACE MODE** to **LIVE** in the frontend. The Vite development
server proxies /api to http://127.0.0.1:8000. Alternatively, set
VITE_API_MODE=live and optionally set VITE_API_BASE_URL in a local
.env.local file before starting Vite. Live API failures remain visible and
offer a deliberate switch to demo mode; they never trigger sample data fallback.

Useful commands:

```sh
npm run typecheck
npm test
npm run build
```

See the frontend architecture guide in ../docs/architecture/frontend.md for API behavior
and current limitations.
