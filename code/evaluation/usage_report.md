# Final-run usage and cost report

Source SHA-256: `eae4344312e149cac5e7a62ac51ff15cd9f3912fe8f8d5797465d1f0cf20c0ad`. Request CSV SHA-256: `7505a4d31e6fb35d77280c55b224290c5ebb2dd1ce21019222a5f190454bbb2d`.

Verified full-dataset run: 518 requests; 2905 normalized observations; 94 evidence files. The summary's output SHA-256 matches root output.csv: `dc87451b3dc72908a60e7852c6429a5d643931aeb884560bf9a5447ff7731769`. Elapsed extraction/index/prediction time: 2.785 seconds. Extraction counters: {'cache_hits': 15}.

## Model/provider totals

| Provider / component | Model or recorded backend | Calls in final run | Input tokens | Output tokens | Total tokens | Estimated API cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Generative model provider | None (local pipeline selected by participant) | 0 | 0 | 0 | 0 | 0.000000 |
| Local extraction: Windows.Media.Ocr | Windows.Media.Ocr | 0 | N/A | N/A | N/A | 0.000000 |
| Overall token-based inference | None | 0 | 0 | 0 | 0 | 0.000000 |

Average per request: 0.000000 input tokens, 0.000000 output tokens, 0.000000 total tokens, and estimated API cost $0.000000. Overall estimated API cost is $0.000000. Local compute, electricity, development time, and operating-system licensing are excluded from API cost.

PDF/OCR extraction is local and has no input/output token accounting. Cache hits are reported separately from new extraction calls; a warm run does not imply that OCR executed again. Cached text derives from supplied artifacts, never cached predictions or public answer labels. The backend table reports only the backend metadata recorded by the run; it does not assume Microsoft OCR when Tesseract or another adapter was used.

Development harnesses and exact session model identifiers are recorded in root log.txt. Development token/cost totals are not measured by this audit pipeline and are not represented as zero. They are separate from runtime audit usage. No remote-model credentials are required or embedded in this local submission.
