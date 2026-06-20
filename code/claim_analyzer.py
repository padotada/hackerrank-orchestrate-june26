from pathlib import Path
from PIL import Image
import base64
import io
import json
from typing import Optional

ALLOWED_ISSUES = {
    "dent", "scratch", "crack", "glass_shatter", "broken_part",
    "missing_part", "torn_packaging", "crushed_packaging",
    "water_damage", "stain", "none", "unknown"
}

ALLOWED_SEVERITY = {"none", "low", "medium", "high", "unknown"}

ALLOWED_RISK_FLAGS = {
    "none", "blurry_image", "cropped_or_obstructed", "low_light_or_glare",
    "wrong_angle", "wrong_object", "wrong_object_part", "damage_not_visible",
    "claim_mismatch", "possible_manipulation", "non_original_image",
    "text_instruction_present", "user_history_risk", "manual_review_required"
}

ALLOWED_PARTS = {
    "car": {
        "front_bumper", "rear_bumper", "door", "hood", "windshield",
        "side_mirror", "headlight", "taillight", "fender",
        "quarter_panel", "body", "unknown"
    },
    "laptop": {
        "screen", "keyboard", "trackpad", "hinge", "lid",
        "corner", "port", "base", "body", "unknown"
    },
    "package": {
        "box", "package_corner", "package_side", "seal",
        "label", "contents", "item", "unknown"
    }
}

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
            prompt = (f"""
You are analyzing an image for a damage claim.

Return ONLY valid JSON. Do not include markdown or explanation outside JSON.

User claim:
{user_claim}

Claim object:
{claim_object}

Use the image as the primary source of truth.

Return this JSON schema:
{{
  "visible_object_type": "car|laptop|package|unknown",
  "object_visible": true or false,
  "claimed_part_visible": true or false,
  "damage_visible": true or false,
  "issue_type": "dent|scratch|crack|glass_shatter|broken_part|missing_part|torn_packaging|crushed_packaging|water_damage|stain|none|unknown",
  "object_part": "one allowed object_part value",
  "quality_assessment": "clear|blurry_image|cropped_or_obstructed|low_light_or_glare|wrong_angle|non_original_image|unknown",
  "risk_flags": "semicolon-separated allowed risk flags, or none",
  "severity": "none|low|medium|high|unknown",
  "visual_justification": "short image-grounded explanation"
}}

Allowed car object_part values:
front_bumper, rear_bumper, door, hood, windshield, side_mirror, headlight, taillight, fender, quarter_panel, body, unknown

Allowed laptop object_part values:
screen, keyboard, trackpad, hinge, lid, corner, port, base, body, unknown

Allowed package object_part values:
box, package_corner, package_side, seal, label, contents, item, unknown

Allowed risk_flags:
none, blurry_image, cropped_or_obstructed, low_light_or_glare, wrong_angle, wrong_object, wrong_object_part, damage_not_visible, claim_mismatch, possible_manipulation, non_original_image, text_instruction_present, user_history_risk, manual_review_required

Important rules:
- object_part must be exactly one allowed value.
- issue_type must be exactly one allowed value.
- severity must be exactly one allowed value.
- risk_flags must only use allowed values.
- If the relevant part is visible and no damage is present, use issue_type="none", damage_visible=false, and risk_flags="damage_not_visible".
- If the issue cannot be determined, use issue_type="unknown".
- Do not invent risk flags.
"""
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

def normalize_analysis(analysis, claim_object):
    claim_object = str(claim_object).lower()

    issue = str(analysis.get("issue_type", "unknown")).lower().strip()
    if issue not in ALLOWED_ISSUES:
        issue = "unknown"

    severity = str(analysis.get("severity", "unknown")).lower().strip()
    if severity == "minor":
        severity = "low"
    elif severity == "moderate":
        severity = "medium"
    elif severity == "severe":
        severity = "high"
    elif severity not in ALLOWED_SEVERITY:
        severity = "unknown"

    part = str(analysis.get("object_part", "unknown")).lower().strip()
    part = part.replace(" ", "_")

    allowed_parts = ALLOWED_PARTS.get(claim_object, {"unknown"})
    if part not in allowed_parts:
        part = "unknown"

    raw_flags = str(analysis.get("risk_flags", "none")).lower()
    flags = set()

    for flag in raw_flags.split(";"):
        flag = flag.strip().replace(" ", "_")

        # common model outputs mapped to allowed values
        if flag in {"no_visible_damage", "damage_absent"}:
            flag = "damage_not_visible"
        if flag in {"motion_blur", "vehicle_in_motion"}:
            flag = "wrong_angle"

        if flag in ALLOWED_RISK_FLAGS and flag != "none":
            flags.add(flag)

    risk_flags = ";".join(sorted(flags)) if flags else "none"

    analysis["issue_type"] = issue
    analysis["severity"] = severity
    analysis["object_part"] = part
    analysis["risk_flags"] = risk_flags

    return analysis
