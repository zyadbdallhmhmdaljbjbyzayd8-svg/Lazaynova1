"""LAZAYNOVA Internal AI Gateway.

Runs LAZAYNOVA native L3 checkpoints locally.
No external model weights.
No external AI APIs.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from urllib.parse import urlparse

import torch

from modules.native_models.l3.model import LazaynovaL3
from modules.native_models.l3.tokenizer import ByteTokenizer
from inference.generate import UTF8ConstrainedGenerator


ROOT = Path(__file__).resolve().parents[2]

CHECKPOINT_PATH = (
    ROOT / "native_ai/checkpoints/l3_checkpoint_v3.pt"
)

SUPPORTED_FORMATS = {
    "LAZAYNOVA_L3_CHECKPOINT_V2",
    "LAZAYNOVA_L3_CHECKPOINT_V3",
    "LAZAYNOVA_L3_CHECKPOINT_V4",
}


class InternalAIGateway:
    """Local inference gateway for native LAZAYNOVA L3."""

    def __init__(
        self,
        local_endpoint="http://127.0.0.1:8788/v1/chat/completions",
        checkpoint_path=None,
        max_new_tokens=64,
    ):
        parsed = urlparse(local_endpoint)

        if (
            parsed.scheme != "http"
            or parsed.hostname not in (
                "127.0.0.1",
                "localhost",
                "::1",
            )
            or parsed.username
            or parsed.password
        ):
            raise PermissionError(
                "Only HTTP loopback endpoints are allowed"
            )

        self.local_endpoint = local_endpoint

        self.checkpoint_path = (
            Path(checkpoint_path)
            if checkpoint_path is not None
            else CHECKPOINT_PATH
        )

        self.max_new_tokens = max(
            1,
            min(int(max_new_tokens), 128),
        )

        self.tokenizer = ByteTokenizer()

        self.model = None
        self.generator = None

        self.model_status = "NOT_LOADED"
        self.model_error = None
        self.checkpoint_format = None

        self._lock = threading.RLock()

        torch.set_num_threads(1)

    def load_model(self, required=False):
        """Load and strictly validate the native checkpoint."""

        with self._lock:

            if self.model is not None:
                return self.model

            if not self.checkpoint_path.is_file():
                self.model_status = "CHECKPOINT_MISSING"

                error = FileNotFoundError(
                    f"Native checkpoint not found: "
                    f"{self.checkpoint_path}"
                )

                self.model_error = str(error)

                if required:
                    raise error

                return None

            try:
                payload = torch.load(
                    self.checkpoint_path,
                    map_location="cpu",
                    weights_only=True,
                )

                if not isinstance(payload, dict):
                    raise ValueError(
                        "Checkpoint payload must be a dictionary"
                    )

                checkpoint_format = payload.get("format")

                if checkpoint_format not in SUPPORTED_FORMATS:
                    raise ValueError(
                        f"Unsupported checkpoint format: "
                        f"{checkpoint_format}"
                    )

                config = payload.get("config")

                if not isinstance(config, dict):
                    raise ValueError(
                        "Checkpoint model configuration is missing"
                    )

                if config.get("external_weights") is not False:
                    raise PermissionError(
                        "External model weights are forbidden"
                    )

                if config.get("external_ai_apis") is not False:
                    raise PermissionError(
                        "External AI APIs are forbidden"
                    )

                if (
                    config.get("tokenizer")
                    != "native_utf8_byte"
                ):
                    raise ValueError(
                        "Unsupported tokenizer configuration"
                    )

                if (
                    int(config.get("vocab_size", -1))
                    != self.tokenizer.VOCAB_SIZE
                ):
                    raise ValueError(
                        "Checkpoint vocabulary mismatch"
                    )

                tokenizer_info = payload.get("tokenizer", {})

                if (
                    tokenizer_info.get("vocab_size")
                    != self.tokenizer.VOCAB_SIZE
                ):
                    raise ValueError(
                        "Checkpoint tokenizer metadata mismatch"
                    )

                state = payload.get("model_state_dict")

                if not isinstance(state, dict) or not state:
                    raise ValueError(
                        "Checkpoint model weights are missing"
                    )

                model = LazaynovaL3(config).cpu()

                model.load_state_dict(
                    state,
                    strict=True,
                )

                for name, parameter in model.state_dict().items():
                    if not torch.isfinite(parameter).all().item():
                        raise ValueError(
                            f"Non-finite model parameter: {name}"
                        )

                model.eval()

                generator = UTF8ConstrainedGenerator(
                    model=model,
                    tokenizer=self.tokenizer,
                    max_new_tokens=self.max_new_tokens,
                    repetition_penalty=1.15,
                    repetition_window=48,
                )

                self.model = model
                self.generator = generator

                self.checkpoint_format = checkpoint_format
                version = checkpoint_format.rsplit("_V", 1)[-1]
                self.model_status = f"READY_NATIVE_SCRATCH_V{version}"

                self.model_error = None

                return self.model

            except Exception as exc:
                self.model = None
                self.generator = None
                self.model_status = "INVALID_CHECKPOINT"
                self.model_error = (
                    f"{type(exc).__name__}: {exc}"
                )

                if required:
                    raise

                return None

    def model_status_report(self):
        """Report local checkpoint status without loading model weights."""

        with self._lock:
            exists = self.checkpoint_path.is_file()

            if self.model is not None:
                status = self.model_status
            elif self.model_status == "INVALID_CHECKPOINT":
                status = self.model_status
            elif exists:
                status = "CHECKPOINT_AVAILABLE"
            else:
                status = "CHECKPOINT_MISSING"

            return {
                "brand": "LAZAYNOVA",
                "native_l3": status,
                "checkpoint_format": self.checkpoint_format,
                "checkpoint_path": str(self.checkpoint_path),
                "checkpoint_exists": exists,
                "checkpoint_available": exists,
                "model_loaded": self.model is not None,
                "external_weights": False,
                "external_ai_apis": False,
                "device": "cpu",
                "error": self.model_error,
            }

    def _prepare_prompt(self, prompt):
        """Keep the prompt within context without splitting UTF-8 bytes."""

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(
                "Prompt must be a non-empty string"
            )

        model = self.load_model(required=True)

        context = int(
            model.config["context_length"]
        )

        clean = prompt.strip()

        already_formatted = (
            clean.startswith("User:")
            and clean.rstrip().endswith("Assistant:")
        )

        if already_formatted:
            formatted = clean
        else:
            prefix = "User: "
            suffix = "\nAssistant:"

            fixed_size = len(
                self.tokenizer.encode(prefix + suffix)
            )

            available = max(
                1,
                context - fixed_size - 1,
            )

            raw = clean.encode("utf-8")

            if len(raw) > available:
                raw = raw[-available:]

                # Ignore only a possible incomplete leading UTF-8
                # sequence introduced by left-side truncation.
                clean = raw.decode(
                    "utf-8",
                    errors="ignore",
                )

            formatted = prefix + clean + suffix

        return formatted

    def generate(
        self,
        prompt,
        max_tokens=None,
        temperature=0.0,
    ):
        """Generate text using the native L3 checkpoint."""

        if not isinstance(prompt, str):
            raise TypeError("Prompt must be text")

        if len(prompt) > 12000:
            raise ValueError(
                "Prompt exceeds the 12000 character limit"
            )

        with self._lock:

            self.load_model(required=True)

            formatted = self._prepare_prompt(prompt)

            count = (
                self.max_new_tokens
                if max_tokens is None
                else max(
                    1,
                    min(
                        int(max_tokens),
                        self.max_new_tokens,
                    ),
                )
            )

            temperature = float(temperature)

            if (
                not torch.isfinite(
                    torch.tensor(temperature)
                ).item()
                or temperature < 0
            ):
                raise ValueError(
                    "Temperature must be finite and non-negative"
                )

            result = self.generator.generate(
                formatted,
                max_tokens=count,
                temperature=temperature,
            )

            if not isinstance(result, str):
                raise RuntimeError(
                    "Native generator returned a non-text result"
                )

            result.encode("utf-8", errors="strict")

            return result.strip()

    def route_request(self, prompt: str, **kwargs) -> dict:
        """Route prompt locally through InternalAIGateway without external calls."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string")
        try:
            output = self.generate(prompt, **kwargs)
            return {
                "status": "ROUTED_LOCALLY",
                "endpoint": getattr(self, "local_endpoint", "local"),
                "response": output,
            }
        except Exception as exc:
            return {
                "status": "ROUTED_LOCALLY",
                "endpoint": getattr(self, "local_endpoint", "local"),
                "response": None,
                "detail": str(exc),
            }

    def chat_completion(
        self,
        messages,
        max_tokens=64,
        temperature=0.0,
    ):
        """Provide a local chat-completion compatible response."""

        if not isinstance(messages, list) or not messages:
            raise ValueError(
                "Messages must be a non-empty array"
            )

        parts = []

        for item in messages[-8:]:

            if not isinstance(item, dict):
                raise ValueError(
                    "Each message must be an object"
                )

            role = item.get("role")
            content = item.get("content", "")

            if role not in (
                "system",
                "user",
                "assistant",
            ):
                raise ValueError(
                    f"Unsupported message role: {role}"
                )

            if not isinstance(content, str):
                raise ValueError(
                    "Message content must be text"
                )

            label = {
                "system": "System",
                "user": "User",
                "assistant": "Assistant",
            }[role]

            parts.append(
                f"{label}: {content.strip()}"
            )

        parts.append("Assistant:")

        prompt = "\n".join(parts)

        output = self.generate(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return {
            "id": "lz-" + os.urandom(8).hex(),
            "object": "chat.completion",
            "model": "LAZAYNOVA-L3-native-v3",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": output,
                    },
                    "finish_reason": "stop",
                }
            ],
        }
