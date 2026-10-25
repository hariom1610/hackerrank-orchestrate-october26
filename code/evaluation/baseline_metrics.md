# Independently measured public baseline

These aggregates were reproduced through the production predictor before the master-prompt fixes. They are evaluation metadata, not inference labels. No case answers or identity/resource mappings are stored here.

Baseline source SHA-256: `4377bad3aafaebe0354414461181176386099c0b38b6e3f3256720d4f6e9d75e`.
Baseline root output SHA-256: `dc87451b3dc72908a60e7852c6429a5d643931aeb884560bf9a5447ff7731769`.
Baseline prediction-input SHA-256: `e2c5c44458c2daafc0b5b64529b4dfdc0f10bd7139aadbd5dc75a5c4a08d4799`.

## Aggregate measurements

```json
{
  "kind": "independently_measured_public_baseline",
  "source_sha256": "4377bad3aafaebe0354414461181176386099c0b38b6e3f3256720d4f6e9d75e",
  "dataset_sha256": "e2c5c44458c2daafc0b5b64529b4dfdc0f10bd7139aadbd5dc75a5c4a08d4799",
  "output_sha256": "dc87451b3dc72908a60e7852c6429a5d643931aeb884560bf9a5447ff7731769",
  "metrics": {
    "requests": 32,
    "status_correct": 29,
    "row_correct": 9,
    "sequence_correct": 9,
    "exact_steps": 114,
    "expected_steps": 193,
    "predicted_steps": 164,
    "field_correct": 957,
    "field_total": 1379,
    "phases": {
      "FINDING": {
        "expected": 41,
        "predicted": 42,
        "matched": 41
      },
      "REMEDIATION": {
        "expected": 41,
        "predicted": 42,
        "matched": 41
      },
      "VERIFICATION": {
        "expected": 111,
        "predicted": 80,
        "matched": 77
      }
    }
  }
}
```

The evaluator-only diagnostic utility uses this aggregate block if the original disposable baseline cache is absent. Baseline figures are not replaced by the final run's measurements.
