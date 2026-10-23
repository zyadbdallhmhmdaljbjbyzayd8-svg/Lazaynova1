#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

BRANCH="$(git branch --show-current)"

if [ -z "$BRANCH" ]; then
  echo "خطأ: لا يوجد فرع Git حالي."
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "خطأ: لم يتم إعداد remote باسم origin."
  exit 1
fi

if [ -z "$(git status --porcelain)" ]; then
  echo "لا توجد تغييرات جديدة للحفظ."
  exit 0
fi

echo "الفرع الحالي: $BRANCH"
echo "فحص الملفات الحساسة..."

git add -A

if git diff --cached --name-only | grep -E '(^|/)(\.env($|\.)|id_rsa|id_ed25519|.*\.keystore$|.*\.jks$|secrets\.json$|credentials\.json$)' >/dev/null; then
  echo "توقف: توجد ملفات حساسة ضمن التغييرات المجهزة."
  echo "راجع git status وملفات staged قبل المتابعة."
  exit 1
fi

if git diff --cached --no-ext-diff | grep -E '^\+.*(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)' >/dev/null; then
  echo "توقف: قد يحتوي التغيير على مفتاح سري."
  echo "راجع التغييرات قبل الرفع."
  exit 1
fi

git diff --cached --check

MESSAGE="${*:-Save Lazaynova progress}"
git commit -m "$MESSAGE"

echo "تم إنشاء الحفظ المحلي."
echo "جارٍ رفع التغييرات إلى الفرع: $BRANCH"

git push -u origin "$BRANCH"

echo "نجح الحفظ والرفع إلى GitHub."
