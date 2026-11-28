# Lazaynova Cloud API

Cloudflare Worker API for Lazaynova.

## Routes

- GET /health
- POST /v1/chat

## Required secrets

- AI_API_KEY
- AUTH_TOKEN

## Variables

- AI_BASE_URL
- AI_MODEL
- ALLOWED_ORIGIN

Never put secrets in frontend code or Git.

This is the initial protected inference gateway.
Production deployment still requires user authentication,
rate limiting, persistent conversation storage, abuse controls,
monitoring, and provider quota management.