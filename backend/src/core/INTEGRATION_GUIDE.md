# دليل الربط - المرحلة الأولى

تم إنشاء الملفات التالية:
- `core/ModelRegistry.ts`
- `external_ai/ExternalBridge.ts`

لربطها بخادمك الحالي (`server.ts`):
1. أضف هذا السطر في أعلى `server.ts`:
   `import { getModelForEngine } from "./core/ModelRegistry.js";`
   `import { ExternalBridge } from "./external_ai/ExternalBridge.js";`

2. في دالة `aiGateway`، يمكنك الآن إضافة منطق التوجيه للنماذج الخارجية.
