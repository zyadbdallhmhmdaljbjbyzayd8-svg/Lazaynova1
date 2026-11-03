# Lazaynova Tiny — local training and inference

This educational character-level GPT starts from random weights. It does not download pretrained weights or call a hosted AI API.

## Termux

```bash
pkg install python-torch python-numpy
python -c "import torch; print(torch.__version__)"
```

Train a checkpoint from the repository root:

```bash
python model/train.py
```

The default training configuration is relatively heavy for a low-memory phone. Test with reduced temporary settings before attempting the full run. The checkpoint is stored in `model/artifacts/lazaynova-tiny.pt` and should not be committed.

## Start local inference

After training creates the checkpoint:

```bash
python model/serve.py
```

The service binds to `127.0.0.1:8080` and supports `GET /health`, `GET /v1/models`, and non-streaming `POST /v1/chat/completions`. This matches the default base URL expected by `backend/src/ai/InternalAIGateway.ts` (`http://127.0.0.1:8080/v1`) when both processes run in the same Termux environment.

Test from another Termux session:

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/v1/models
curl -fsS http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"lazaynova-core","messages":[{"role":"user","content":"مرحبا"}],"max_tokens":16}'
```

Optional variables: `LAZAYNOVA_HOST`, `LAZAYNOVA_PORT`, `LAZAYNOVA_CHECKPOINT`. Keep the server on loopback; this prototype has no authentication and must not be exposed publicly.

## Limitations

The tokenizer is character-level and ignores characters absent from the training vocabulary. The current sample corpus is tiny, so output will likely be poor or nonsensical. This endpoint proves local inference wiring, not assistant-level quality. Image/video/music catalog entries remain planning helpers until real compatible models and runtimes are supplied. Train only on data you have permission to use; do not train on private personal data.
