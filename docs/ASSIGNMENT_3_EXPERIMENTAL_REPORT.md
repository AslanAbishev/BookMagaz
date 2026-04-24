# Assignment 3: Experimental Engineering

This report captures the performance, mutation, and chaos experiments executed
for the GoodBooks system. All experiments were designed to be reproducible in a
local development environment without requiring a production MongoDB instance.

## Scope

- System under test: GoodBooks Flask + MongoDB web application
- Critical modules:
  - `backend/app.py`
  - `backend/models.py`
  - `backend/recommend.py`
- Experiment evidence directory:
  - `docs/experimental_evidence/`

## 1. Performance Testing

### Test Plan

| Scenario | Load level | Requests | Expected result |
| --- | --- | ---: | --- |
| Home page `/` | expected / stress / extreme | 20 / 75 / 150 | Route stays below 50 ms average with zero errors |
| Search API `/api/search` | expected / stress / extreme | 20 / 75 / 150 | Search remains stable with zero errors |
| Recommend API `/api/recommend/<user>` | expected / stress / extreme | 20 / 75 / 150 | Recommendation endpoint remains stable with zero errors |
| Product page `/product/<id>` | expected / stress / extreme | 20 / 75 / 150 | Product rendering remains stable with zero errors |
| Profile page `/profile` | expected / stress / extreme | 20 / 75 / 150 | Authenticated profile rendering remains stable with zero errors |

### Execution

Command:

```powershell
venv\Scripts\python.exe scripts\experimental_performance.py
```

Artifacts:

- `docs/experimental_evidence/performance_results.csv`
- `docs/experimental_evidence/performance_results.json`
- `docs/experimental_evidence/performance_run.txt`

### Results Summary

| Scenario | Avg response time range | P95 range | Peak throughput | Errors |
| --- | --- | --- | --- | --- |
| Home page `/` | 0.50-1.20 ms | 0.60-1.50 ms | 1898.01 rps | 0 |
| Search API | 0.21-0.23 ms | 0.25-0.33 ms | 4385.50 rps | 0 |
| Recommend API | 0.84-1.24 ms | 1.12-1.84 ms | 1153.69 rps | 0 |
| Product page | 0.77-1.18 ms | 0.99-1.57 ms | 1246.80 rps | 0 |
| Profile page | 1.15-1.67 ms | 1.48-2.31 ms | 847.84 rps | 0 |

### Analysis

- The fastest scenario was `search_api`, which stayed near `0.22 ms` even at extreme load.
- The slowest scenario was `profile_page`, which reached `1.67 ms` average and `2.31 ms` p95 under expected load.
- `recommend_api` was the second-heaviest path, which is consistent with recommendation scoring and cache access.
- No scenario produced errors, so experimental availability under the deterministic load model was `100%`.
- The main bottleneck candidate is profile aggregation because it combines user lookup, recommendation building, and history assembly in one request.

### Recommendations

- Cache or precompute profile summary fragments for high-traffic users.
- Keep recommendation cache warm before heavier profile traffic.
- If this is scaled to a real database-backed load test, focus on the profile and recommendation flows first.

## 2. Mutation Testing

### Mutation Plan

| Mutant ID | Module | Mutation | Rationale |
| --- | --- | --- | --- |
| M1 | `backend/models.py` | Remove lowercase normalization in `create_user` | Check whether data-layer validation tests catch broken normalization |
| M2 | `backend/app.py` | Replace rating range `or` with `and` | Check whether invalid rating tests detect weakened validation |
| M3 | `backend/app.py` | Invert duplicate-like guard | Check whether repeated action tests catch duplicate interactions |
| M4 | `backend/recommend.py` | Break cold-start branch | Check whether recommendation tests detect cold-start regressions |
| M5 | `backend/recommend.py` | Raise similarity threshold | Check whether similar-book ranking tests detect weakened recommendations |
| M6 | `backend/models.py` | Disable category filter participation in search | Check whether search tests detect category filtering regressions |

### Execution

Command:

```powershell
venv\Scripts\python.exe scripts\experimental_mutation.py
```

Artifacts:

- `docs/experimental_evidence/mutation_results.csv`
- `docs/experimental_evidence/mutation_results.json`
- `docs/experimental_evidence/mutation_run.txt`

### Results Summary

| Mutant ID | Module | Status | Observation |
| --- | --- | --- | --- |
| M1 | `backend/models.py` | killed | Email normalization regression detected by model tests |
| M2 | `backend/app.py` | killed | Rating validation weakness detected by API tests |
| M3 | `backend/app.py` | killed | Duplicate-like guard inversion detected by repeated-action API tests |
| M4 | `backend/recommend.py` | survived | Cold-start branch mutant survived focused recommendation test |
| M5 | `backend/recommend.py` | survived | Strict similarity threshold mutant survived focused similarity test |
| M6 | `backend/models.py` | killed | Search category-filter regression detected by search/model tests |

### Mutation Score Calculation

- Total valid mutants: `6`
- Killed mutants: `4`
- Surviving mutants: `2`
- Mutation score: `4 / 6 * 100 = 66.67%`

### Analysis

- The suite is strong in `models.py` and API validation logic: all corresponding mutants were killed.
- The surviving mutants are both in `recommend.py`, which indicates that the recommendation tests still verify coarse output shape better than detailed ranking sensitivity.
- M4 surviving suggests the cold-start test checks returned titles/order but does not yet guarantee the precise branch behavior strongly enough.
- M5 surviving suggests the similar-book assertions should become stricter around ranking sensitivity and score thresholds.

### Recommendations

- Add more explicit assertions on recommendation order and the source of fallback results.
- Add tests that compare expected recommendation sets before and after score-threshold changes.
- Expand mutation coverage in `recommend.py` before the final paper so the recommendation layer does not remain the weakest experimental area.

## 3. Chaos / Fault Injection Testing

### Chaos Plan

| Scenario | Fault injected | Expected resilience behavior |
| --- | --- | --- |
| Search API | `search_books` raises exception | API returns controlled error and recovers on next request |
| Recommend API | recommendation engine raises exception | Fault should be observable; recovery should succeed after fault removal |
| Product page | `get_book` raises exception | Fault should be observable; recovery should succeed after fault removal |
| Profile page | `get_user_by_id` returns `None` | Session should be cleared and user redirected to login |
| Admin rebuild | `build_item_similarity` raises exception | Endpoint should show handled failure message and recover next run |

### Execution

Command:

```powershell
venv\Scripts\python.exe scripts\experimental_chaos.py
```

Artifacts:

- `docs/experimental_evidence/chaos_results.csv`
- `docs/experimental_evidence/chaos_results.json`
- `docs/experimental_evidence/chaos_run.txt`

### Results Summary

| Scenario | Fault status | Graceful degradation | Recovery status | Recovery time |
| --- | --- | --- | --- | --- |
| Search API | 500 | no | 200 | 0.54 ms |
| Recommend API | 500 | no | 200 | 25.54 ms |
| Product page | 500 | no | 200 | 12.86 ms |
| Profile page | 302 | yes | 200 | 10.43 ms |
| Admin rebuild | 200 | yes | 200 | 6.01 ms |

### Chaos Metrics

- Fault scenarios executed: `5`
- Graceful degradation cases: `2 / 5`
- Successful recovery after fault removal: `5 / 5`
- Average recovery time: `11.08 ms`

### Analysis

- The strongest resilience behavior was seen in `profile_page`, which redirected to login when the user context disappeared.
- `admin_rebuild` also degraded gracefully by surfacing an error message without taking down the route.
- `search_api`, `recommend_api`, and `product_page` all escalated to HTTP `500`, which shows weak fault isolation for runtime exceptions in those flows.
- Despite the 500s, every scenario recovered immediately after fault removal, so the application state was not permanently corrupted by the injected failures.

### Recommendations

- Add route-level exception handling for recommendation and product detail flows.
- Standardize API fault responses into JSON error envelopes instead of raw 500 pages.
- Consider fallback behavior for recommendation failures so the profile and recommendation routes can degrade to popular books rather than failing hard.

## 4. Analysis

The three experimental tracks complement each other:

- Performance experiments show the deterministic test environment is fast and stable, with profile and recommendation flows remaining the slowest but still comfortably below a few milliseconds in the in-memory setup.
- Mutation experiments show that validation and model rules are well protected, while recommendation ranking logic still has assertion gaps.
- Chaos experiments show recovery is strong, but fault containment is uneven because several critical routes still surface raw 500 failures.

Taken together, the experimental results indicate that GoodBooks has solid baseline robustness, but the recommendation layer remains the main engineering improvement target for the next phase.

## 5. Reproducibility

All experiments use deterministic in-memory data through:

- `scripts/experimental_common.py`
- `tests/helpers.py`

This avoids external database drift and makes the results repeatable for the
final paper.

### Re-run Commands

```powershell
venv\Scripts\python.exe scripts\experimental_performance.py
venv\Scripts\python.exe scripts\experimental_mutation.py
venv\Scripts\python.exe scripts\experimental_chaos.py
```

### Evidence Index

- `docs/experimental_evidence/performance_results.csv`
- `docs/experimental_evidence/performance_results.json`
- `docs/experimental_evidence/performance_run.txt`
- `docs/experimental_evidence/mutation_results.csv`
- `docs/experimental_evidence/mutation_results.json`
- `docs/experimental_evidence/mutation_run.txt`
- `docs/experimental_evidence/chaos_results.csv`
- `docs/experimental_evidence/chaos_results.json`
- `docs/experimental_evidence/chaos_run.txt`

### Limitations

- The experiments intentionally run against deterministic in-memory collections rather than a live MongoDB server, because the assignment focuses on controlled, reproducible engineering experiments.
- This means the reported timings are engineering baselines, not production deployment timings.
- For a future extension, the same scripts can be paired with a live MongoDB-backed environment to compare controlled versus integrated runtime behavior.
