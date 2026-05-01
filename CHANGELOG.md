# Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-05-01 | Multi-month unified report: `generateFinancialReport` now accepts a `{"months": [...]}` payload and renders a single comparative report across all periods (no per-month files). Added `not_applicable` label for Runway and Burn Multiple when the business is cash flow positive (replaces incorrect `insufficient_data`). Added industry confidence gate: agent must self-assess `business_type` confidence and block on the user when below ~80%, surfacing `industry_confidence` and `industry_reasoning` in the report header. |
| 1.0.0 | 2026-04-30 | First public release. Broadened from SaaS-only to multi-business analysis. Added strict insufficient_data behavior, missing input diagnostics, reusable bank CSV normalizer, period guidance, and updated docs/evals for publish readiness. |
