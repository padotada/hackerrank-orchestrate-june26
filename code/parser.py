ISSUE_KEYWORDS = {
    "dent": ["dent", "dented"],
    "scratch": ["scratch", "scratched", "scrape", "scuff"],
    "crack": ["crack", "cracked"],
    "glass_shatter": ["shattered", "smashed glass", "glass broke"],
    "broken_part": ["broken", "broke", "snapped", "damaged"],
    "missing_part": ["missing", "came off", "fell off"],
    "torn_packaging": ["torn", "ripped", "opened", "seal broken"],
    "crushed_packaging": ["crushed", "crumpled", "smashed box"],
    "water_damage": ["water", "wet", "liquid", "coffee"],
    "stain": ["stain", "stained", "mark"],
}

PART_KEYWORDS = {
    "car": {
        "front_bumper": ["front bumper"],
        "rear_bumper": ["rear bumper", "back bumper"],
        "door": ["door"],
        "hood": ["hood"],
        "windshield": ["windshield", "front glass"],
        "side_mirror": ["side mirror", "mirror"],
        "headlight": ["headlight"],
        "taillight": ["taillight"],
        "fender": ["fender"],
        "quarter_panel": ["quarter panel"],
        "body": ["body", "panel"],
    },
    "laptop": {
        "screen": ["screen", "display"],
        "keyboard": ["keyboard", "keys", "keycaps"],
        "trackpad": ["trackpad", "touchpad"],
        "hinge": ["hinge"],
        "lid": ["lid"],
        "corner": ["corner"],
        "port": ["port", "usb", "charging"],
        "base": ["base", "bottom"],
        "body": ["body", "case", "casing"],
    },
    "package": {
        "box": ["box"],
        "package_corner": ["corner"],
        "package_side": ["side"],
        "seal": ["seal", "tape"],
        "label": ["label"],
        "contents": ["contents", "inside"],
        "item": ["item", "product"],
    }
}

def parse_claim(user_claim, claim_object):
    text = str(user_claim).lower()
    claim_object = str(claim_object).lower()

    claimed_issue = "unknown"
    claimed_part = "unknown"

    for issue, keywords in ISSUE_KEYWORDS.items():
        if any(k in text for k in keywords):
            claimed_issue = issue
            break

    for part, keywords in PART_KEYWORDS.get(claim_object, {}).items():
        if any(k in text for k in keywords):
            claimed_part = part
            break

    text_instruction_present = any(
        phrase in text
        for phrase in [
            "approve the claim",
            "skip manual review",
            "ignore previous instructions",
            "mark this supported",
            "mark this row supported",
        ]
    )

    return {
        "claimed_issue_type": claimed_issue,
        "claimed_object_part": claimed_part,
        "text_instruction_present": text_instruction_present,
    }