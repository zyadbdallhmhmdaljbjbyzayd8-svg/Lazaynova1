#!/data/data/com.termux/files/usr/bin/bash
set -eu
cd "$(dirname "$0")/.."
test -f model/train.py
test -f model/config.json
test -f backend/src/ai/InternalAIGateway.ts
if [ -e model/serve.py ] || [ -e model/test_serve.py ] || [ -e model/LOCAL_RUNTIME.md ]; then
  echo "Refusing to overwrite existing local-runtime files. Review/backup them first."
  exit 2
fi
cp payload/model/serve.py model/serve.py
cp payload/model/test_serve.py model/test_serve.py
cp payload/model/README.md model/LOCAL_RUNTIME.md
echo "Installed model/serve.py, model/test_serve.py and model/LOCAL_RUNTIME.md."
echo "Existing model/README.md, training config, backend source, Android source and Git state were not changed."
