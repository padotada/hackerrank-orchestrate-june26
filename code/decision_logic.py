from parser import parse_claim
def values_match(claimed, visible):
    claimed = str(claimed).lower()
    visible = str(visible).lower()

    if claimed in ["unknown", "none", ""]:
        return True

    if visible in ["unknown", "none", ""]:
        return False

    if claimed == visible:
        return True

    # Allow some nearby matches
    compatible = {
        "crack": {"glass_shatter", "broken_part"},
        "glass_shatter": {"crack", "broken_part"},
        "scratch": {"stain"},
        "torn_packaging": {"crushed_packaging"},
        "crushed_packaging": {"torn_packaging"},
    }

    return visible in compatible.get(claimed, set())


def determine_claim_status(claim, analysis, valid_image, evidence_met):
    if not valid_image:
        return (
            "not_enough_information",
            "No valid image could be loaded for visual review."
        )

    if evidence_met != "true":
        return (
            "not_enough_information",
            "Image evidence does not meet the minimum visibility or quality standard."
        )

    parsed = parse_claim(claim.get("user_claim", ""))

    claimed_issue = parsed["claimed_issue_type"]
    claimed_part = parsed["claimed_object_part"]

    visible_issue = str(analysis.get("issue_type", "unknown")).lower()
    visible_part = str(analysis.get("object_part", "unknown")).lower()
    risk_flags = str(analysis.get("risk_flags", "none")).lower()

    if "wrong_object" in risk_flags:
        return (
            "contradicted",
            "The image appears to show the wrong object type for this claim."
        )

    if "damage_not_visible" in risk_flags and visible_part == claimed_part:
        return (
            "contradicted",
            "The claimed object part is visible, but the claimed damage is not visible."
        )

    part_matches = values_match(claimed_part, visible_part)
    issue_matches = values_match(claimed_issue, visible_issue)

    if visible_issue not in ["unknown", "none", ""] and part_matches and issue_matches:
        return (
            "supported",
            f"The image shows visible {visible_issue} on the {visible_part}, matching the user's claim."
        )

    if visible_issue not in ["unknown", "none", ""] and not issue_matches:
        return (
            "contradicted",
            f"The image shows {visible_issue}, but the user claimed {claimed_issue}."
        )

    if visible_part not in ["unknown", "none", ""] and not part_matches:
        return (
            "not_enough_information",
            f"The image shows the {visible_part}, but the claimed part appears to be {claimed_part}."
        )

    return (
        "not_enough_information",
        "The image was reviewed, but the relevant claimed damage could not be verified."
    )