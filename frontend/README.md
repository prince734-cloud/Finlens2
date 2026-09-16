# FinLens frontend

## Local development

From this directory:

```bash
npm install
npm run dev
```

The Vite development proxy sends `/api` requests to `http://127.0.0.1:8000`.

## Vercel deployment

Create a Vercel project from this repository with:

- Root Directory: `FinLens/frontend`
- Framework Preset: `Vite`
- Build Command: `npm run build`
- Output Directory: `dist`

Add this environment variable in Vercel, using the public Railway URL:

```text
VITE_API_BASE_URL=https://<railway-domain>/api/v1
```

The SPA rewrite in `vercel.json` keeps client-side routes working after refresh.

## Railway backend

Create a Railway service from the same repository and set its Root Directory to
`FinLens`. Railway will use the included `Dockerfile` and `railway.toml`.

Set these Railway variables:

```text
GROQ_API_KEY=...
CORS_ORIGINS=https://<vercel-domain>
DATABASE_URL=postgresql+asyncpg://...
```

Use a Railway PostgreSQL service for production data. The default SQLite and
Chroma files are suitable for local development, but Railway containers have
ephemeral storage unless a volume is attached.
