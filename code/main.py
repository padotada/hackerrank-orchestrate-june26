from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
import os
import anthropic

load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME", "claude-opus-4-6")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def get_anthropic_client():
    """
    Return (client, model_name) or (None, None) if Anthropic is not configured or unavailable.
    """
    if not ANTHROPIC_API_KEY:
        return None, None
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return client, MODEL_NAME
    except Exception:
        return None, None
    
OUTPUT_COLUMNS = [
    "user_id",
    "image_paths",
    "user_claim",
    "claim_object",
    "evidence_standard_met",
    "evidence_standard_met_reason",
    "risk_flags",
    "issue_type",
    "object_part",
    "claim_status",
    "claim_status_justification",
    "supporting_image_ids",
    "valid_image",
    "severity",
]

def main():
    root = Path(__file__).resolve().parents[1]
    dataset_dir = root / "dataset"
    claims = pd.read_csv(dataset_dir / "claims.csv")
    history = pd.read_csv(dataset_dir / "user_history.csv")
    requirements = pd.read_csv(dataset_dir / "evidence_requirements.csv")
    rows = []
    client, model = get_anthropic_client()
    try:
        from claim_analyzer import ClaimAnalyzer
    except Exception:
        ClaimAnalyzer = None

    analyzer = ClaimAnalyzer(client=client, model=model) if ClaimAnalyzer else None

    for _, claim in claims.iterrows():
        image_paths = str(claim.get("image_paths", ""))
        imgs = [p.strip() for p in image_paths.split(";") if p.strip()]

        analysis = {
            "issue_type": "unknown",
            "object_part": "unknown",
            "quality_assessment": "unknown",
            "risk_flags": "none",
            "severity": "unknown",
        }
        supporting_ids = []
        valid_image = False

        for img_rel in imgs:
            img_path = root / img_rel
            if analyzer:
                b64 = analyzer.load_image(img_path)
            else:
                b64 = None
            if not b64:
                continue
            valid_image = True
            if analyzer:
                result = analyzer.analyze_image(b64, claim_object=claim.get("claim_object"))
            else:
                result = {
                    "issue_type": "unknown",
                    "object_part": "unknown",
                    "quality_assessment": "clear",
                    "risk_flags": "none",
                    "severity": "unknown",
                }
            analysis = result
            img_id = Path(img_rel).stem
            supporting_ids.append(img_id)
            # analyze only first usable image for now
            break

        evidence_met = "true" if analysis.get("quality_assessment", "") in ["clear", "good", "clear_image", "clear"] and valid_image else "false"
        evidence_reason = "Image quality acceptable" if evidence_met == "true" else "Insufficient image quality or missing images"

        row = {
            "user_id": claim["user_id"],
            "image_paths": claim["image_paths"],
            "user_claim": claim["user_claim"],
            "claim_object": claim["claim_object"],
            "evidence_standard_met": evidence_met,
            "evidence_standard_met_reason": evidence_reason,
            "risk_flags":  analysis.get("risk_flags", "none"),
            "issue_type": analysis.get("issue_type", "unknown"),
            "object_part": analysis.get("object_part", "unknown"),
            "claim_status": "not_enough_information",
            "claim_status_justification": "Automated image analysis completed; final reasoning not yet implemented.",
            "supporting_image_ids": ";".join(supporting_ids) if supporting_ids else "none",
            "valid_image": "true" if valid_image else "false",
            "severity": analysis.get("severity", "unknown"),
        }
        rows.append(row)
    output = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    output.to_csv(root / "output.csv", index=False)

if __name__ == "__main__":
    main()