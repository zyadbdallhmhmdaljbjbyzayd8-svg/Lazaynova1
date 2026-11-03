#!/usr/bin/env bash
set -euo pipefail
FAIL=0

# لا تستخدم -- هنا: grep يجب أن يرى هذه كخيارات، لا كمسارات.
EXCLUDES=(
  --exclude-dir=node_modules
  --exclude-dir=.git
  --exclude-dir=dist
  --exclude-dir=build
  --exclude-dir=.gradle
  --exclude-dir=.next
  --exclude-dir=self-hosted-ai
  --exclude='audit-no-external-apis.sh'
  --exclude='*.backup-*'
  --exclude='*.bak'
  --exclude='*.lock'
  --exclude='pnpm-lock.yaml'
)

URL_PATTERNS=(
  'api\.openai\.com' 'api\.anthropic\.com'
  'generativelanguage\.googleapis\.com' 'api\.cohere\.ai'
  'api\.mistral\.ai' 'api\.groq\.com' 'api\.together\.xyz'
  'api\.perplexity\.ai' 'openai\.azure\.com'
)
ENV_KEYS=(
  'OPENAI_API_KEY' 'OPENAI_ORG_ID' 'ANTHROPIC_API_KEY'
  'GOOGLE_API_KEY' 'GEMINI_API_KEY' 'COHERE_API_KEY'
  'MISTRAL_API_KEY' 'GROQ_API_KEY' 'TOGETHER_API_KEY'
  'PERPLEXITY_API_KEY' 'HUGGINGFACE_API_KEY' 'REPLICATE_API_TOKEN'
)
SDK_KEYS=(
  '"openai"[[:space:]]*:'
  '"@anthropic-ai/sdk"[[:space:]]*:'
  '"@google/generative-ai"[[:space:]]*:'
  '"cohere-ai"[[:space:]]*:'
  '"@mistralai/mistralai"[[:space:]]*:'
  '"groq-sdk"[[:space:]]*:'
)

scan() {
  local label="$1"; shift
  local pat matches
  for pat in "$@"; do
    matches=$(grep -rInE "${EXCLUDES[@]}" -e "$pat" . 2>/dev/null || true)
    if [ -n "$matches" ]; then
      echo "$matches"
      echo "❌ $label: $pat"
      FAIL=1
    fi
  done
}

echo "==> Lazaynova external-API audit"
scan "Provider URL"      "${URL_PATTERNS[@]}"
scan "Forbidden env key" "${ENV_KEYS[@]}"
scan "Forbidden SDK dep" "${SDK_KEYS[@]}"

matches=$(grep -rInE "${EXCLUDES[@]}" \
  -e '(sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{35})' \
  . 2>/dev/null || true)
if [ -n "$matches" ]; then
  echo "$matches"
  echo "❌ Secret-shaped string found"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "✅ Clean. No external AI references found."
  exit 0
else
  echo "🚫 Audit FAILED."
  exit 1
fi
