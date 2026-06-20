ISSUE_KEYWORDS = {
    "dent": ["dent", "bent", "deformation", "hail dent", "hail dents"],
    "scratch": ["scratch", "scrape", "scuff", "mark"],
    "crack": ["crack", "cracked"],
    "glass_shatter": ["shatter", "shattered", "broken glass", "glass broken"],
    "broken_part": ["broken", "damaged", "snapped", "off"],
    "missing_part": ["missing", "gone", "absent"],
    "torn_packaging": ["torn", "tear"],
    "crushed_packaging": ["crushed", "squashed", "flattened"],
    "water_damage": ["water damage", "wet", "soaked", "damp"],
    "stain": ["stain", "stained", "spot"],
}

PART_KEYWORDS = {
    "front_bumper": ["front bumper", "bumper"],
    "rear_bumper": ["rear bumper"],
    "door": ["door", "door panel"],
    "hood": ["hood", "bonnet"],
    "windshield": ["windshield", "front glass", "wind screen"],
    "side_mirror": ["side mirror", "mirror"],
    "headlight": ["headlight", "head lamp"],
    "taillight": ["taillight", "tail light"],
    "fender": ["fender"],
    "quarter_panel": ["quarter panel"],
    "screen": ["screen", "display"],
    "keyboard": ["keyboard"],
    "trackpad": ["trackpad", "touchpad"],
    "hinge": ["hinge"],
    "lid": ["lid"],
    "corner": ["corner"],
    "port": ["port", "charging port"],
    "box": ["box"],
    "seal": ["seal", "sealed"],
    "label": ["label"],
    "contents": ["contents"],
    "item": ["item", "product"],
}

def parse_claim(user_claim):
    text = str(user_claim).lower()

    claimed_issue = "unknown"
    claimed_part = "unknown"

    for issue, keywords in ISSUE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            claimed_issue = issue
            break

    for part, keywords in PART_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            claimed_part = part
            break

    return {
        "claimed_issue_type": claimed_issue,
        "claimed_object_part": claimed_part,
    }