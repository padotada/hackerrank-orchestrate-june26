from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
import os
import anthropic
from claim_analyzer import ClaimAnalyzer, normalize_analysis
from decision_logic import determine_claim_status
from parser import parse_claim
    
root = Path(__file__).resolve().parents[1]
load_dotenv(root / ".env")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "claude-opus-4-6")

print(f"API Key set: {bool(ANTHROPIC_API_KEY)}")
print(f"Model: {MODEL_NAME}")
        
def get_anthropic_client():
    """
    Return (client, model_name) or (None, None) if Anthropic is not configured or unavailable.
    """
    if not ANTHROPIC_API_KEY:
        return None, None
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return client, MODEL_NAME
    except Exception as e:
        print("Failed to create Anthropic client:", e)
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

def resolve_image_path(root, dataset_dir, img_rel):
    img_rel = str(img_rel).strip()
    rel_path = Path(img_rel)
    candidates = [
        root / rel_path,
        dataset_dir / rel_path,
        dataset_dir / "images" / rel_path,
        dataset_dir / "images" / "test" / rel_path,
        dataset_dir / "images" / "test" / rel_path.name,
    ]

    for path in candidates:
        if path.exists():
            return path

    return None

def combine_flags(*flag_strings):
    flags = set()
    for flag_string in flag_strings:
        if not isinstance(flag_string, str):
            continue

        for flag in flag_string.split(";"):
            flag = flag.strip()

            if flag and flag.lower() != "none":
                flags.add(flag)
            
    return ";".join(sorted(flags)) if flags else "none"

def main():
    dataset_dir = root / "dataset"
    claims = pd.read_csv(dataset_dir / "claims.csv")
    history = pd.read_csv(dataset_dir / "user_history.csv")
    requirements = pd.read_csv(dataset_dir / "evidence_requirements.csv")
    history_by_user = history.set_index("user_id").to_dict("index")

    rows = []
    client, model = get_anthropic_client()

    analyzer = ClaimAnalyzer(client=client, model=model) if ClaimAnalyzer else None

    for _, claim in claims.iterrows():
        parsed_claim = parse_claim( claim.get("user_claim", ""), claim.get("claim_object", ""))
        user_history = history_by_user.get(claim["user_id"], {})
        history_flags = user_history.get("history_flags", "none")
        claim_text_flag = ("text_instruction_present" if parsed_claim.get("text_instruction_present") else "none")
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
            img_path = resolve_image_path(root, dataset_dir, img_rel)
            print("Image path:", img_path)
            if analyzer:
                b64 = analyzer.load_image(img_path)
            else:
                b64 = None
            if not b64:
                print("Image not loaded")
                continue
            valid_image = True
            if analyzer:
                result = analyzer.analyze_image(b64, claim_object=claim.get("claim_object"), user_claim=claim.get("user_claim"))
            else:
                result = {
                    "issue_type": "unknown",
                    "object_part": "unknown",
                    "quality_assessment": "clear",
                    "risk_flags": "none",
                    "severity": "unknown",
                }
            result = normalize_analysis(result, claim.get("claim_object"))
            analysis = result
            print("Analysis:", analysis)
            img_id = Path(img_rel).stem
            supporting_ids.append(img_id)
            # analyze only first usable image for now
            break

        evidence_met = "true" if analysis.get("quality_assessment", "") in ["clear", "good", "clear_image", "clear"] and valid_image else "false"
        claim_status, claim_status_justification = determine_claim_status(claim, parsed_claim, analysis, valid_image, evidence_met,)
        combined_risk_flags = combine_flags(
    analysis.get("risk_flags", "none"),
    history_flags,
    claim_text_flag,
)
        evidence_reason = "Image quality acceptable" if evidence_met == "true" else "Insufficient image quality or missing images"

        row = {
            "user_id": claim["user_id"],
            "image_paths": claim["image_paths"],
            "user_claim": claim["user_claim"],
            "claim_object": claim["claim_object"],
            "evidence_standard_met": evidence_met,
            "evidence_standard_met_reason": evidence_reason,
            "risk_flags": combined_risk_flags,
            "issue_type": analysis.get("issue_type", "unknown"),
            "object_part": analysis.get("object_part", "unknown"),
            "claim_status": claim_status,
            "claim_status_justification": claim_status_justification,
            "supporting_image_ids": ";".join(supporting_ids) if supporting_ids else "none",
            "valid_image": "true" if valid_image else "false",
            "severity": analysis.get("severity", "unknown"),
        }
        rows.append(row)
    output = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    output.to_csv(root / "output.csv", index=False)

if __name__ == "__main__":
    main()