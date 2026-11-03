#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
cd "$HOME/Lazaynova-repo"

echo "=== 1. فحص الفرع وحالة Git ==="
BRANCH="$(git branch --show-current)"
test -n "$BRANCH" || { echo "لا يوجد فرع حالي"; exit 1; }
git status --short --branch

echo "=== 2. تطوير توجيه المحركات ==="
python - <<'PY'
from pathlib import Path

p = Path("backend/src/server.ts")
s = p.read_text(encoding="utf-8")

start = "function routeIntent(s: string): Intent {"
end = "\n}\n\n// --- ROUTES ---"
a = s.find(start)
b = s.find(end, a) if a >= 0 else -1

new_router = '''function routeIntent(s: string): Intent {
  const t = s.toLowerCase();

  if (/\\b(music|song|audio|موسيقى|اغنية|أغنية|لحن|صوت)\\b/.test(t)) {
    return "music";
  }
  if (/\\b(video|film|movie|فيديو|فلم|مشاهد|مونتاج)\\b/.test(t)) {
    return "video";
  }
  if (/\\b(agent|team|multi.?agent|فريق|وكلاء|نفذ المهمة|نفّذ المهمة)\\b/.test(t)) {
    return "agent";
  }
  if (/\\b(research|بحث عميق|ابحث|مصادر|تحليل بحثي)\\b/.test(t)) {
    return "research";
  }
  if (/\\b(code|debug|program|coding|برمج|كود|خطأ برمجي)\\b/.test(t)) {
    return "coding";
  }
  if (/\\b(document|pdf|file|مستند|ملف|لخص الوثيقة|لخص المستند)\\b/.test(t)) {
    return "documents";
  }
  if (/\\b(image|picture|draw|صورة|صور|ارسم|تصميم صورة)\\b/.test(t)) {
    return "image";
  }
  return "chat";
}'''

if a < 0 or b < 0:
    if "LAZAYNOVA_ENGINE_ROUTING_V1" not in s:
        raise SystemExit("لم أتعرف على موضع routeIntent المتوقع؛ أوقفت التعديل.")
else:
    s = s[:a] + "// LAZAYNOVA_ENGINE_ROUTING_V1\n" + new_router + s[b + len("\n}"):]
    p.write_text(s, encoding="utf-8")
    print("تم تحديث توجيه الطلبات.")

old = '''    // Use Local Gateway for direct chat
    const response = await gateway.chat({
      model: "lazaynova-core",
      messages: [
        { role: "system", content: "أنت مساعد Lazaynova الذكي." },
        { role: "user", content: parsed.message }
      ]
    });

    res.json({ type: "chat", intent: intentKind, response });'''

new = '''    // Route the request to its specialist engine.
    const engineId = routeIntent(parsed.message);
    const specialist = agents[engineId];

    const response = await gateway.chat({
      model: "lazaynova-core",
      messages: [
        { role: "system", content: specialist.system },
        ...(parsed.history ?? []).slice(-10).map((item) => ({
          role: item.role,
          content: item.content
        })),
        { role: "user", content: parsed.message }
      ],
      temperature: 0.3,
      max_tokens: 700,
      stream: false
    });

    res.json({
      type: "chat",
      intent: engineId,
      engine: specialist.name,
      response
    });'''

if old in s:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("تم ربط المحادثة بتعليمات المحرك المتخصص.")
elif 'const engineId = routeIntent(parsed.message);' in s and 'engine: specialist.name' in s:
    print("ربط المحركات موجود بالفعل.")
else:
    raise SystemExit("لم أتعرف على موضع بوابة المحادثة المتوقع؛ أوقفت التعديل.")
PY

echo "=== 3. فحص سلامة التغييرات ==="
git diff --check

echo "=== 4. اختبارات Backend ==="
npm --prefix backend test

echo "=== 5. بناء TypeScript ==="
npm --prefix backend run build

echo "=== 6. مراجعة التغيير ==="
git diff -- backend/src/server.ts
git diff --check

echo "=== 7. حفظ الملف المطوّر فقط ==="
git add -- backend/src/server.ts scripts/build-engine-core.sh

if git diff --cached --quiet; then
  echo "لا توجد تغييرات جديدة للحفظ."
  exit 0
fi

git diff --cached --check
git diff --cached --stat
git commit -m "Activate specialist engine routing"

echo "=== 8. رفع التغيير إلى GitHub ==="
git push origin "HEAD:refs/heads/$BRANCH"

echo "=== 9. الحالة النهائية ==="
git status --short --branch
echo "نجحت مرحلة نواة المحركات."
