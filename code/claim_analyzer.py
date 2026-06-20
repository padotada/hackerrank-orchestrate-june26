from pathlib import Path
from PIL import Image
import base64
import io
import json
from typing import Optional


class ClaimAnalyzer:
    """Load images and analyze them with Anthropic when available."""

    def __init__(self, client=None, model=None):
        self.client = client
        self.model = model

    def parse_claim(self, user_claim: str) -> str:
        if not isinstance(user_claim, str):
            return ""
        return user_claim.strip()

    def load_image(self, path) -> Optional[str]:
        p = Path(path)
        if not p.exists():
            return None
        try:
            img = Image.open(p).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            print("Image didn't exist")
            return None

    def _extract_text(self, response) -> str:
        if response is None:
            return ""
        content = getattr(response, "content", None)
        if isinstance(content, list):
            parts = []
            for block in content:
                block_type = getattr(block, "type", None)
                if block_type == "text":
                    parts.append(getattr(block, "text", ""))
                elif isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            if parts:
                return "\n".join(parts)
        if isinstance(content, str):
            return content
        completion = getattr(response, "completion", None)
        if isinstance(completion, str):
            return completion
        return str(response)

    def _parse_model_response(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except Exception:
                    pass
        return {
            "issue_type": "unknown",
            "object_part": "unknown",
            "quality_assessment": "unknown",
            "risk_flags": "none",
            "severity": "unknown",
            "raw_text": text,
        }

    def analyze_image(self, image_b64: str, claim_object: Optional[str] = None, user_claim = None) -> dict:
        if self.client and self.model:
            # print(f"DEBUG: Calling Claude with model={self.model}, claim_object={claim_object}")
            # print(f"DEBUG: Image b64 length={len(image_b64) if image_b64 else 0}")
            prompt = (
                "Analyze this image for a damage claim. Return only valid JSON with keys:\n"
    "- visible_object_type\n"
    "- object_visible\n"
    "- claimed_part_visible\n"
    "- damage_visible\n"
    "- issue_type\n"
    "- object_part\n"
    "- quality_assessment\n"
    "- risk_flags\n"
    "- severity\n"
    "- visual_justification\n\n"
    f"Claim object: {claim_object}\n"
    f"User claim: {user_claim}\n\n"
    "Allowed issue_type values: dent, scratch, crack, glass_shatter, broken_part, "
    "missing_part, torn_packaging, crushed_packaging, water_damage, stain, none, unknown.\n"
    "Allowed severity values: none, minor, moderate, severe, unknown.\n"
    "quality_assessment should be one of: clear, blurry, cropped_or_obstructed, "
    "low_light_or_glare, wrong_angle, non_original_image, unknown.\n"
    "risk_flags should be a semicolon-separated string or none.\n"
    "Use the image as the primary source of truth. Do not assume damage that is not visible."
            )
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=512,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_b64,
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                )
                text = self._extract_text(response)
                return self._parse_model_response(text)
            except Exception as e:
                return {
                    "issue_type": "unknown",
                    "object_part": "unknown",
                    "quality_assessment": "unknown",
                    "risk_flags": "none",
                    "severity": "unknown",
                    "error": str(e),
                }
        return {
            "issue_type": "unknown",
            "object_part": "unknown",
            "quality_assessment": "clear",
            "risk_flags": "none",
            "severity": "unknown",
        }
