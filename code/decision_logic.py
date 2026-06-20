def to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower().strip() == "true"


def compatible_issue(claimed, visible):
    if claimed in {"unknown", "", "none"}:
        return visible not in {"unknown", ""}

    if claimed == visible:
        return True

    compatible = {
        "crack": {"glass_shatter", "broken_part"},
        "glass_shatter": {"crack", "broken_part"},
        "broken_part": {"crack", "glass_shatter", "missing_part"},
        "torn_packaging": {"crushed_packaging"},
        "crushed_packaging": {"torn_packaging"},
    }

    return visible in compatible.get(claimed, set())


def determine_claim_status(claim, parsed_claim, analysis, valid_image, evidence_met):
    if not valid_image:
        return (
            "not_enough_information",
            "No valid image could be loaded for automated review."
        )

    if evidence_met != "true":
        return (
            "not_enough_information",
            "The submitted image is not sufficient to evaluate the claimed damage."
        )

    risk_flags = str(analysis.get("risk_flags", "none")).lower()
    claimed_issue = parsed_claim["claimed_issue_type"]
    claimed_part = parsed_claim["claimed_object_part"]

    visible_issue = str(analysis.get("issue_type", "unknown")).lower()
    visible_part = str(analysis.get("object_part", "unknown")).lower()

    claimed_part_visible = to_bool(analysis.get("claimed_part_visible", False))
    damage_visible = to_bool(analysis.get("damage_visible", False))

    if "wrong_object" in risk_flags:
        return (
            "contradicted",
            "The submitted image appears to show a different object than the claim describes."
        )

    if not claimed_part_visible:
        return (
            "not_enough_information",
            "The image does not clearly show the claimed object part."
        )

    if claimed_part_visible and not damage_visible:
        return (
            "contradicted",
            "The claimed object part is visible, but the claimed damage is not visible."
        )

    if damage_visible and visible_issue not in {"none", "unknown", ""}:
        if compatible_issue(claimed_issue, visible_issue):
            return (
                "supported",
                f"The image shows visible {visible_issue} on the {visible_part}, matching the claim."
            )

        return (
            "contradicted",
            f"The image shows {visible_issue}, but the claim describes {claimed_issue}."
        )

    return (
        "not_enough_information",
        "The image was reviewed, but the visible evidence was not enough to verify the claim."
    )