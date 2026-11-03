# Lazaynova Tiny — first from-scratch model

This is the first educational model component for Lazaynova. It initializes a small GPT-style transformer with random weights and trains it on text supplied by the project owner. It does **not** use a hosted AI API or download pretrained weights.

## Requirements
- Python 3.10+
- PyTorch
- For practical training, a computer or cloud machine with adequate RAM/compute is recommended. Termux on a phone may not support standard PyTorch installation and is not a realistic environment for meaningful training.

## Run
From the repository root:

```bash
python -m pip install -r model/requirements.txt
python model/train.py
```

The trained checkpoint is written to `model/artifacts/lazaynova-tiny.pt`. Artifacts are generated locally and should not be committed to Git.

## Important limitations
- The tokenizer is character-level, intentionally simple.
- The included text is a tiny demonstration sample, not a capable training corpus.
- The model is a prototype for validating a training pipeline; it will not behave like ChatGPT.
- Use only text you have permission to train on. Keep private or personal data out of the training set.
- This first step does not yet connect inference to the existing Express API. That integration should be implemented and tested as a separate step.
