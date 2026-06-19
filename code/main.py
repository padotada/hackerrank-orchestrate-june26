from pathlib import Path
import pandas as pd

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
    for _, claim in claims.iterrows():
        row = {
            "user_id": claim["user_id"],
            "image_paths": claim["image_paths"],
            "user_claim": claim["user_claim"],
            "claim_object": claim["claim_object"],
            "evidence_standard_met": "false",
            "evidence_standard_met_reason": "Baseline placeholder; visual review not yet implemented.",
            "risk_flags": "none",
            "issue_type": "unknown",
            "object_part": "unknown",
            "claim_status": "not_enough_information",
            "claim_status_justification": "No image analysis has been performed yet.",
            "supporting_image_ids": "none",
            "valid_image": "false",
            "severity": "unknown",
        }
        rows.append(row)
    output = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    output.to_csv(root / "output.csv", index=False)

if __name__ == "__main__":
    main()