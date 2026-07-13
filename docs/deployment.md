# Deployment checklist

## DNS

- `caos.thinkred.ru` -> TimeWeb static hosting.
- `api-caos.thinkred.ru` -> VPS public IP.

## VPS

- Install Docker and the Compose plugin.
- Copy `.env.example` to `.env`, replace every default secret.
- Keep database and Redis ports bound only to the Docker network.
- Put Nginx in front of port 8000 and issue a certificate with the existing VPS certificate workflow.
- Run `docker compose up -d --build db redis backend`.
- Verify `https://api-caos.thinkred.ru/health` and `https://api-caos.thinkred.ru/docs`.

## Frontend

```powershell
$env:VITE_API_URL = "https://api-caos.thinkred.ru/api/v1"
npm ci
npm run build
```

Upload the generated `frontend/dist` contents to the TimeWeb document root. Configure SPA fallback to `index.html` if the hosting panel supports it.
