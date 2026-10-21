# Lazaynova Android app

This is a native Android app written in Kotlin and Jetpack Compose, not a WebView wrapper.

## Build
1. Open the repository root in Android Studio.
2. Install Android SDK Platform 35 and JDK 17 if prompted.
3. Let Gradle sync, then run the `app` configuration on an emulator or device.
4. Build an APK from **Build > Build APK(s)**.

## API connection
The default `http://10.0.2.2:8787` is for an Android emulator when the API is running on the development computer.

For a physical phone, use a deployed HTTPS API URL:
`gradle assembleDebug -PAPI_BASE_URL=https://YOUR-API-HOST`

Never put an AI provider key in the Android app. Keep `AI_API_KEY` on the server.

## Scope
The app includes Arabic native UI, specialist shortcuts, current-session chat, loading/error states, and API integration. The backend routes requests to one specialist intent and one configured AI model. This is the base for a fuller autonomous multi-agent system, not a claim that all autonomous tools are already implemented. User accounts, database-backed chat, web-search tools, file processing, billing, monitoring and production deployment still need additional work and configuration.

Official Compose setup: https://developer.android.com/develop/ui/compose/setup
