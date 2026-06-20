# Evaluation Report

## 1. System Overview

This solution uses a hybrid vision-language and rule-based pipeline to verify damage claims. The system reads each row from `dataset/claims.csv`, loads the submitted local images, sends each usable image to a Claude vision-capable model for structured visual analysis, normalizes the model output to the allowed schema, and then applies deterministic Python rules to decide whether the claim is `supported`, `contradicted`, or `not_enough_information`.

The main design principle is that the image is treated as the primary source of truth. The user conversation is used to determine what damage and object part should be checked. User history is used only to add risk context through `risk_flags`; it does not override clear visual evidence.

## 2. Pipeline

The implemented pipeline is:

```text
claims.csv
  -> claim parser
  -> image path resolver
  -> image loader/base64 encoder
  -> Claude vision analyzer
  -> output normalization
  -> evidence validator
  -> rule-based claim decision
  -> user history risk aggregation
  -> output.csv generation
```

The vision model is asked to return structured JSON containing:

* visible object type
* whether the object is visible
* whether the claimed part is visible
* whether damage is visible
* visible issue type
* relevant object part
* image quality assessment
* risk flags
* severity
* short image-grounded justification

A deterministic post-processing layer then constrains these values to the allowed output labels from the problem statement.

## 3. Evaluation Method

The system was evaluated using `dataset/sample_claims.csv`, which contains labeled examples with expected outputs. The evaluation compares the generated predictions against the expected labels for key fields, including:

* `claim_status`
* `evidence_standard_met`
* `issue_type`
* `object_part`
* `valid_image`
* `severity`

The most important evaluation target is `claim_status`, since it represents the final verification decision. Other fields are used to diagnose why the system is correct or incorrect.

The evaluation script is located at:

```text
code/evaluation/main.py
```

It can be run after generating predictions for the sample set.

## 4. Strategy Comparison

Two strategies were considered.

### Strategy A: Direct Final-Answer Prompting

In this approach, the model would receive the claim and image and directly generate the final output row. This is simpler, but it has several drawbacks:

* The model may invent values outside the allowed schema.
* The model may mix visual evidence with user history too strongly.
* It is harder to debug individual errors.
* The final decision may be less reproducible.

### Strategy B: Structured Visual Extraction + Rule-Based Decision

The final solution uses this strategy. The model only extracts visible evidence from the image, while Python code applies the final claim verification rules.

Advantages:

* Easier to enforce allowed output values.
* Easier to debug each stage.
* User history can be kept separate from visual verification.
* Final claim status is more reproducible.
* The system can normalize model outputs before writing `output.csv`.

For these reasons, Strategy B was selected as the final approach.

## 5. Evidence Decision Rules

The rule-based decision layer follows these principles:

```text
No valid image
  -> not_enough_information

Image quality or visibility is insufficient
  -> not_enough_information

Wrong object is shown
  -> contradicted

Claimed part is not visible
  -> not_enough_information

Claimed part is visible and no damage is visible
  -> contradicted

Claimed part is visible and matching damage is visible
  -> supported

Damage is visible but does not match the claim
  -> contradicted
```

The evidence standard is considered met when the image is usable and the relevant object/part is visible clearly enough to evaluate the claim.

## 6. Risk Handling

Risk flags are aggregated from three sources:

1. Image analysis, such as blurry images, wrong angle, wrong object, or damage not visible.
2. User claim text, such as prompt-injection-like instructions asking the system to approve the claim.
3. User history, such as repeated rejected claims or manual review patterns.

User history is used only for risk context. It does not change a visually supported claim into a contradicted claim by itself.

## 7. Model Calls

The system currently analyzes the first usable image for each claim. Therefore, the approximate number of model calls is:

```text
number of processed rows with at least one valid image
```

For the sample set:

```text
approximately one model call per sample claim with a valid image
```

For the test set:

```text
approximately one model call per test claim with a valid image
```

If multiple images are analyzed per claim in a future version, the number of model calls would increase up to the total number of image paths across all rows.

## 8. Token Usage Estimate

Each request includes:

* one image
* a structured instruction prompt
* the user claim text
* the claim object
* JSON schema instructions

Approximate text token usage per request:

```text
Input text tokens: 600-1,200
Output tokens: 100-300
```

Image token usage depends on the model provider's image processing rules, image size, and internal encoding. Images are resized/converted before upload to reduce unnecessary payload size.

For a rough estimate, assuming one image per claim:

```text
Total input tokens ~= number_of_claims * 1,000 text tokens + image processing tokens
Total output tokens ~= number_of_claims * 200 output tokens
```

## 9. Cost Estimate

The implementation uses an Anthropic Claude model configured through the `MODEL_NAME` environment variable. Pricing depends on the selected model. As a pricing assumption, recent Anthropic public model pages list Opus-family pricing around **$5 per million input tokens and $25 per million output tokens**, while Sonnet-family pricing is lower at about **$3 per million input tokens and $15 per million output tokens**. These rates should be checked against the current Anthropic pricing page before final submission.

Using the Opus assumption and ignoring image-specific billing differences, the approximate text-only cost per 100 claims is:

```text
Input: 100 claims * 1,000 input tokens = 100,000 input tokens
Output: 100 claims * 200 output tokens = 20,000 output tokens

Input cost: 0.1M * $5 = $0.50
Output cost: 0.02M * $25 = $0.50

Approximate text-only total: $1.00 per 100 claims
```

Actual cost may be higher because image inputs may be billed differently from text-only tokens. The system reduces unnecessary cost by processing only the first usable image per claim in the baseline version.

## 10. Runtime and Latency

Runtime is dominated by remote model calls. Estimated latency is:

```text
2-8 seconds per image call, depending on model latency, image size, and network conditions
```

For 100 claims with one image each, sequential runtime may be roughly:

```text
3-13 minutes
```

This can be reduced through batching or limited concurrency, as long as API rate limits are respected.

## 11. TPM/RPM Considerations

The system should consider both tokens-per-minute and requests-per-minute limits.

Current mitigation strategy:

* Process one image per claim in the baseline.
* Avoid repeated calls for images that cannot be loaded.
* Keep the prompt compact and schema-focused.
* Use deterministic normalization and decision logic instead of additional LLM reasoning calls.
* Add retry logic for transient API failures.
* Optionally cache model responses by image path and claim text during development.

Potential future improvements:

* Add local response caching.
* Add configurable sleep/retry backoff.
* Add limited concurrency with a maximum worker count.
* Analyze additional images only when the first image is insufficient.

## 12. Limitations

The main limitations are:

* The system currently depends on the vision model's ability to correctly identify damage and object parts.
* Some visible damage may be subtle or ambiguous.
* The claim parser is keyword-based and may miss unusual wording.
* The baseline processes only the first usable image, which may miss supporting evidence in later images.
* Model output still requires normalization because vision models may return synonyms or non-allowed values.

## 13. Future Improvements

Future improvements could include:

* Analyze all images for a claim and choose the strongest supporting or contradicting image.
* Use `evidence_requirements.csv` more directly by matching claim object and issue family.
* Improve claim parsing with an LLM or more robust keyword mappings.
* Add caching to reduce repeated development cost.
* Add a confidence score internally for manual review prioritization.
* Generate an error analysis CSV for sample set mistakes.
