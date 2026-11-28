from pathlib import Path
from datetime import datetime
import re
import shutil
import sys

ROOT = Path.cwd()
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
files = {}

def load_file(rel):
    path = ROOT / rel
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {rel}")
    return path.read_text(encoding="utf-8")

def replace_once(rel, old, new):
    current = files[rel][1]
    count = current.count(old)
    if count != 1:
        raise ValueError(
            f"{rel}: expected exactly 1 match, found {count}: {old[:100]!r}"
        )
    files[rel] = (files[rel][0], current.replace(old, new, 1))

def replace_all(rel, old, new, minimum=1):
    current = files[rel][1]
    count = current.count(old)
    if count < minimum:
        raise ValueError(
            f"{rel}: expected at least {minimum} matches, found {count}: {old!r}"
        )
    files[rel] = (files[rel][0], current.replace(old, new))

def load_targets():
    targets = [
        "backend/src/server.ts",
        "backend/src/coordinator/taskDispatcher.ts",
        "backend/src/coordinator/modelSelector.ts",
        "backend/local_bridge/lazaynova_local_server.py",
        "lz_core/ai_gateway/gateway.py",
        "app/src/main/java/com/lazaynova/app/ChatRepository.kt",
        "app.js",
    ]
    for rel in targets:
        path = ROOT / rel
        files[rel] = (path, load_file(rel))

try:
    load_targets()

    # 1) Central TypeScript API listens on 8787.
    replace_once(
        "backend/src/server.ts",
        'const PORT = process.env.PORT ? parseInt(process.env.PORT) : 8788;',
        'const PORT = process.env.PORT ? parseInt(process.env.PORT) : 8787;'
    )

    replace_once(
        "backend/src/server.ts",
        'import { LocalKnowledgeBase } from "./knowledge/knowledgeBase.js";',
        'import { LocalKnowledgeBase } from "./knowledge/knowledgeBase.js";\n'
        'import { CoordinatorService } from "./services/coordinatorService.js";'
    )

    replace_once(
        "backend/src/server.ts",
        'const knowledgeBase = new LocalKnowledgeBase();',
        'const knowledgeBase = new LocalKnowledgeBase();\n'
        'const coordinatorService = new CoordinatorService();'
    )

    # Preserve the existing agent orchestrator route.
    # Route text engines through the coordinator; retain other engines.
    server = files["backend/src/server.ts"][1]
    route_pattern = re.compile(
        r'app\.post\("/api/chat", async \(req, res\) => \{.*?\n\}\);',
        re.DOTALL
    )
    route_matches = list(route_pattern.finditer(server))
    if len(route_matches) != 1:
        raise ValueError(
            "backend/src/server.ts: expected exactly one /api/chat route, "
            f"found {len(route_matches)}"
        )

    new_route = '''app.post("/api/chat", async (req, res) => {
  try {
    const {
      message,
      engineId = "chat",
      useOrchestrator = true,
      maxTokens = 48
    } = req.body ?? {};

    if (typeof message !== "string" || !message.trim()) {
      return res.status(400).json({ error: "Message is required" });
    }

    if (
      !Number.isInteger(maxTokens) ||
      maxTokens < 1 ||
      maxTokens > 96
    ) {
      return res.status(400).json({
        error: "maxTokens must be an integer between 1 and 96"
      });
    }

    if (useOrchestrator && engineId === "agent") {
      const result = await orchestrator.runWorkflow(message, engineId);
      return res.json({
        response: `${result.plan}\\n\\n${result.execution}\\n\\n${result.review}`,
        metadata: {
          orchestrator: true,
          sources: result.knowledgeSourcesCount
        }
      });
    }

    if (["chat", "research", "coding", "documents"].includes(engineId)) {
      const result = await coordinatorService.execute({
        message,
        engineId,
        maxTokens
      });

      return res.json({
        response: result.answer,
        metadata: {
          coordinator: true,
          requestId: result.requestId,
          engineId: result.engineId,
          intent: result.intent,
          language: result.language,
          model: result.model,
          sources: result.sources,
          durationMs: result.durationMs
        }
      });
    }

    // Keep image, video, music and other existing engine handlers intact.
    const result = await engineManager.execute(engineId, message);
    return res.json({
      response: result.output,
      metadata: result.metadata
    });
  } catch (err: any) {
    return res.status(500).json({
      error: err.message || "Internal server error"
    });
  }
});'''

    server = route_pattern.sub(new_route, server, count=1)
    files["backend/src/server.ts"] = (
        files["backend/src/server.ts"][0],
        server
    )

    # 2) Coordinator calls the private Python bridge on 8788.
    replace_once(
        "backend/src/coordinator/taskDispatcher.ts",
        '|| "http://127.0.0.1:8787";',
        '|| "http://127.0.0.1:8788";'
    )
    replace_all(
        "backend/src/coordinator/taskDispatcher.ts",
        "LAZAYNOVA-L3-native-v2",
        "LAZAYNOVA-L3-native-v3"
    )

    # 3) Model selector must recognize the installed V3 checkpoint.
    replace_all(
        "backend/src/coordinator/modelSelector.ts",
        "LAZAYNOVA-L3-native-v2",
        "LAZAYNOVA-L3-native-v3"
    )
    replace_all(
        "backend/src/coordinator/modelSelector.ts",
        "READY_NATIVE_SCRATCH_V2",
        "READY_NATIVE_SCRATCH_V3"
    )

    # 4) Private Python bridge: V3, load checkpoint on status request,
    #    and listen only on loopback port 8788.
    replace_once(
        "backend/local_bridge/lazaynova_local_server.py",
        '"""Threaded loopback REST bridge for LAZAYNOVA native L3 V2."""',
        '"""Private loopback inference bridge for LAZAYNOVA native L3 V3."""'
    )
    replace_all(
        "backend/local_bridge/lazaynova_local_server.py",
        "LAZAYNOVA-L3-native-v2",
        "LAZAYNOVA-L3-native-v3"
    )
    replace_once(
        "backend/local_bridge/lazaynova_local_server.py",
        '        if path=="/api/model/status":\n'
        '            return self._send(200,gateway.model_status_report())',
        '        if path=="/api/model/status":\n'
        '            gateway.load_model(required=False)\n'
        '            return self._send(200,gateway.model_status_report())'
    )
    replace_once(
        "backend/local_bridge/lazaynova_local_server.py",
        'host,port="127.0.0.1",8787',
        'host,port="127.0.0.1",8788'
    )

    # 5) Keep the gateway's default inference endpoint on the private bridge.
    replace_once(
        "lz_core/ai_gateway/gateway.py",
        'local_endpoint="http://127.0.0.1:8787/v1/chat/completions"',
        'local_endpoint="http://127.0.0.1:8788/v1/chat/completions"'
    )

    # 6) Android app uses its configured API host.
    replace_once(
        "app/src/main/java/com/lazaynova/app/ChatRepository.kt",
        'private const val CHAT_URL =\n'
        '            "http://127.0.0.1:8787/api/chat"',
        'private val CHAT_URL =\n'
        '            BuildConfig.API_BASE_URL.trimEnd(\'/\') + "/api/chat"'
    )

    # 7) Web frontend uses the central API.
    replace_once(
        "app.js",
        "const API_BASE_URL = 'http://127.0.0.1:8788';",
        "const API_BASE_URL = 'http://127.0.0.1:8787';"
    )
    replace_once(
        "app.js",
        "تأكد أن خادم المنفذ 8788 يعمل.",
        "تأكد أن الخادم المركزي على المنفذ 8787 يعمل."
    )

except Exception as exc:
    print("PRECHECK FAILED:", exc)
    print("No source files were changed.")
    sys.exit(1)

# Back up all affected files before writing any updated source.
backup_root = ROOT / "backups" / f"centralize-{STAMP}"

try:
    if backup_root.exists():
        raise FileExistsError(f"Backup already exists: {backup_root}")

    for rel, (path, updated) in files.items():
        backup = backup_root / path.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)

    written = []
    try:
        for rel, (path, updated) in files.items():
            path.write_text(updated, encoding="utf-8")
            written.append(rel)
    except Exception:
        # Restore any file already written if a later write fails.
        for rel in written:
            path = files[rel][0]
            backup = backup_root / path.relative_to(ROOT)
            shutil.copy2(backup, path)
        raise

except Exception as exc:
    print("WRITE FAILED:", exc)
    print("Inspect backups at:", backup_root)
    sys.exit(1)

print("CENTRALIZATION PATCH: SUCCESS")
print("Backup directory:", backup_root)
for rel in files:
    print("UPDATED:", rel)
