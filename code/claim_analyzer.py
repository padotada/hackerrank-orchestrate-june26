from pathlib import Path
from PIL import Image
import base64
import io
import json

class ClaimAnalyzer:
    """Load images, parse claims, and analyze images using Anthropic when available.

    Methods:
    - load_image(path): returns base64 JPEG bytes or None
    - analyze_image(image_b64, claim_object=None): returns dict with keys
      issue_type, object_part, quality_assessment, risk_flags, severity
    """
    def __init__(self, client=None, model=None):
        self.client = client
        self.model = model

    def parse_claim(self, user_claim: str) -> str:
        # Lightweight parser (placeholder). Return the claim text normalized.
        if not isinstance(user_claim, str):
            return ""
        return user_claim.strip()

    def load_image(self, path) -> str | None:
        p = Path(path)
        if not p.exists():
            return None
        try:
            img = Image.open(p).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return None

    def _parse_model_response(self, text: str) -> dict:
        # Try to recover JSON from the model response
        try:
            return json.loads(text)
        except Exception:
            # best-effort: look for first { ... } block
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end+1])
                except Exception:
                    pass
        # fallback minimal structure
        return {
            "issue_type": "unknown",
            "object_part": "unknown",
            "quality_assessment": "unknown",
            "risk_flags": "none",
            "severity": "unknown",
            "raw_text": text,
        }

    def analyze_image(self, image_b64: str, claim_object: str | None = None) -> dict:
        # If Anthropic client available, call it with a structured prompt
        if self.client and self.model:
            prompt = (
                "You are an assistant that analyzes a single image for damage claims.\n"
                "Return a JSON object with keys: issue_type, object_part, quality_assessment, risk_flags, severity.\n"
                f"Claim object: {claim_object}\n"
                "Image is provided as base64 JPEG. You do not need to decode it; rely on visual analysis capabilities.\n"
                "Respond only with JSON.\n"
                "Image (first 512 chars, truncated):\n"
                + image_b64[:512]
            )
            try:
                resp = self.client.messages.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                )
                # Attempt to extract a text completion from possible response shapes
                text = ""
                if isinstance(resp, dict):
                    text = resp.get("completion") or resp.get("content") or str(resp)
                else:
                    # Some SDKs attach .content or .completion
                    text = getattr(resp, "completion", None) or getattr(resp, "content", None) or str(resp)
                parsed = self._parse_model_response(text)
                return parsed
            except Exception as e:
                return {
                    "issue_type": "unknown",
                    "object_part": "unknown",
                    "quality_assessment": "unknown",
                    "risk_flags": "none",
                    "severity": "unknown",
                    "error": str(e),
                }
        # Fallback heuristic when no model available
        return {
            "issue_type": "unknown",
            "object_part": "unknown",
            "quality_assessment": "clear",
            "risk_flags": "none",
            "severity": "unknown",
        }
