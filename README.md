# Lazaynova — AI Agent Platform

منصة عربية متعددة الوكلاء: واجهة ويب + API + تطبيق Android أصلي بـ Kotlin وJetpack Compose.

## Components
- `index.html`, `styles.css`, `app.js`: responsive Arabic/English web UI.
- `backend/`: Express + TypeScript API; provider keys stay server-side.
- `app/`: native Android application (not a WebView).
- `docker-compose.yml`: local PostgreSQL, Redis and MinIO services.
- `.github/workflows/`: CI checks and Android APK build.

## Quick start — API
1. Install Node.js 20+.
2. `cd backend && npm install`
3. Copy `.env.example` to `.env` and set `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`.
4. `npm run dev`

The API listens on port `8787`, health endpoint is `/health`, chat endpoint is `POST /api/chat`.

## Web
Serve the repository root with any static web server. The frontend calls `/api/chat` when configured; set `window.LAZAYNOVA_API_BASE` in `app.js` to the deployed API origin if frontend and API are hosted separately.

## Android
Open the repository root in Android Studio, install Android SDK 35 and JDK 17, then run the `app` configuration. Details in `ANDROID_SETUP.md`.

Default Android API address `http://10.0.2.2:8787` is for an Android emulator only. For a real phone, build with a deployed HTTPS API URL:
`gradle assembleDebug -PAPI_BASE_URL=https://YOUR-API-HOST`

Never embed provider API keys in web or Android clients.

## Important scope note
This is a runnable starter/MVP, not a finished production SaaS. The current backend routes a request to a specialist intent and calls one configured AI model. Full autonomous multi-agent planning, user accounts, durable chat storage, web search tools, file processing, billing, monitoring, and production security require additional implementation and configuration.
