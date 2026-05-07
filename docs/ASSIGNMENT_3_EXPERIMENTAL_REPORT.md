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

## Database-Focused Experimental Extension

The lecturer feedback highlighted that a Flask + MongoDB system should not be
evaluated only at the route level. To address this, the experimental pack was
extended with explicit database-oriented checks for:

- data integrity
- query performance
- index verification
- database-specific engineering recommendations

### Execution

```powershell
venv\Scripts\python.exe scripts\experimental_database.py
```

### Database Evidence

- `docs/experimental_evidence/database_integrity_results.csv`
- `docs/experimental_evidence/database_query_results.csv`
- `docs/experimental_evidence/database_index_results.csv`
- `docs/experimental_evidence/database_results.json`
- `docs/experimental_evidence/database_run.txt`

### Database Integrity Summary

| Check | Status | Details |
| --- | --- | --- |
| duplicate_usernames | PASS | No duplicate usernames found |
| duplicate_emails | PASS | No duplicate emails found |
| rating_range_and_type | PASS | Invalid rating count: 0 |
| orphaned_interactions | PASS | Orphaned interaction count: 0 |

### Database Query Performance Summary

| Query | Avg ms | P95 ms | Indexed | Note |
| --- | ---: | ---: | --- | --- |
| find_user_by_username | 0.0026 | 0.0029 | no | users.username unique index missing |
| find_user_by_email | 0.0026 | 0.0027 | no | users.email unique index missing |
| find_book_by_book_id | 0.0036 | 0.0038 | yes | book_id index present |
| find_books_by_category | 0.0116 | 0.0164 | yes | category index present |
| find_interactions_by_user | 0.0065 | 0.0070 | no | interactions.user_id index missing |
| search_books_text_and_category | 0.0215 | 0.0278 | partial | application uses regex fallback rather than a pure text-index path |
| get_popular_books | 0.0206 | 0.0334 | partial | average_rating index exists but ratings_count compound support is missing |

### Database Index Audit

| Collection | Expected index | Priority | Present |
| --- | --- | --- | --- |
| books | book_id_1 | HIGH | yes |
| books | category_1 | MEDIUM | yes |
| books | title_authors_text | MEDIUM | yes |
| users | username_unique | CRITICAL | no |
| users | email_unique | CRITICAL | no |
| interactions | user_id_idx | HIGH | no |
| interactions | book_id_idx | HIGH | no |
| interactions | user_id_1_book_id_1 | HIGH | no |

### Database Findings

- The integrity checks passed, so the sample database model is internally consistent.
- The slowest database-oriented operations are `search_books_text_and_category` and `get_popular_books`, which is consistent with regex-based filtering and sorting logic.
- The most important weakness is not integrity, but missing expected indexes on `users` and `interactions`.
- This means the application-layer tests are not enough on their own; query-path quality also depends on database indexing strategy.

### Database Recommendations

- Add unique indexes for `users.username` and `users.email`.
- Add lookup indexes for `interactions.user_id`, `interactions.book_id`, and ideally a compound `(user_id, book_id)` index.
- Replace or complement regex search with a stronger text-index-backed search path if production-scale search is required.
- Treat database engineering as a first-class QA scope, not just a backend implementation detail.

## Live MongoDB Experimental Extension

To answer the database-focused feedback more directly, the assignment was also
extended with a second experiment that runs against the actual local MongoDB
database instead of a deterministic in-memory stub.

### Execution

```powershell
venv\Scripts\python.exe scripts\experimental_database_live.py
```

### Live MongoDB Evidence

- `docs/experimental_evidence/database_live_integrity_results.csv`
- `docs/experimental_evidence/database_live_query_results.csv`
- `docs/experimental_evidence/database_live_index_results.csv`
- `docs/experimental_evidence/database_live_results.json`
- `docs/experimental_evidence/database_live_run.txt`

### Live Integrity and Schema Summary

| Check | Status | Details |
| --- | --- | --- |
| duplicate_usernames | PASS | No duplicate usernames found |
| duplicate_emails | PASS | Only 6 users currently carry an email field |
| rating_range_and_type | PASS | Invalid rating count: 0 |
| users_name_field_coverage | WARN | 0.01% |
| users_email_field_coverage | WARN | 0.01% |
| books_category_field_coverage | WARN | 0.0% |
| interactions_interaction_field_coverage | WARN | 0.0% |
| interactions_timestamp_field_coverage | WARN | 0.0% |
| sampled_orphaned_interactions | PASS | sampled_user_ids=40, unmatched_sampled_user_ids=0 |

### Live Query Performance Summary

| Query | Avg ms | P95 ms | Plan | Note |
| --- | ---: | ---: | --- | --- |
| find_user_by_username_live | 2.6233 | 4.0767 | COLLSCAN | direct login-style lookup on the live users collection |
| find_user_by_email_live | 0.0 | 0.0 | SCHEMA_GAP | email field is absent in the live users collection |
| find_book_by_book_id_live | 2.9538 | 4.6524 | COLLSCAN | product-detail lookup on the live books collection |
| find_books_by_category_live | 0.0 | 0.0 | SCHEMA_GAP | category field is absent in the live books collection |
| find_interactions_by_user_live | 224.2334 | 239.8534 | COLLSCAN | history/profile lookup on the live interactions collection |
| text_search_books_live | 3.6118 | 4.7297 | TEXT_MATCH | text-index-backed live catalog search |
| get_popular_books_live | 12.8497 | 14.4759 | COLLSCAN | sorted popularity query used by fallback and recommendation flows |

### Live Index Audit

| Collection | Expected index | Priority | Present |
| --- | --- | --- | --- |
| books | title_text_authors_text | MEDIUM | yes |
| books | book_id_1 | HIGH | no |
| books | category_1 | MEDIUM | no |
| users | username_1 | CRITICAL | no |
| users | email_1 | CRITICAL | no |
| interactions | user_id_1 | HIGH | no |
| interactions | book_id_1 | HIGH | no |
| interactions | user_id_1_book_id_1 | HIGH | no |

### Live MongoDB Findings

- The live database reveals a more serious engineering problem than the deterministic baseline: the current persisted schema only partially matches what the Flask application expects.
- Login-style user lookup, product lookup, and interaction-history lookup all degrade to `COLLSCAN`, and the interaction query is especially expensive at roughly `224 ms` average.
- The text-search path is the healthiest live query because the catalog still has a working text index.
- Several application-facing fields that the code expects, including `email`, `category`, `interaction`, and `timestamp`, are mostly absent from the live dataset.

### Live MongoDB Recommendations

- Add production-grade indexes for `users.username`, `users.email`, `books.book_id`, and `interactions.user_id` as the first remediation step.
- Align the live dataset with the current application schema by backfilling `email`, `category`, `interaction`, and `timestamp` where they are required by application logic.
- Treat `find_interactions_by_user_live` as the highest-priority query optimization target because it impacts profile and history flows directly.
- Keep both DB experiments in the final submission: the deterministic baseline proves reproducibility, while the live MongoDB run proves real integration risk.

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
| Home page `/` | 0.47-2.50 ms | 0.50-2.70 ms | 2012.81 rps | 0 |
| Search API | 0.21-0.24 ms | 0.23-0.31 ms | 4479.62 rps | 0 |
| Recommend API | 0.73-1.25 ms | 0.77-1.42 ms | 1317.21 rps | 0 |
| Product page | 0.69-1.15 ms | 0.74-1.88 ms | 1399.86 rps | 0 |
| Profile page | 1.03-1.51 ms | 1.27-1.88 ms | 943.39 rps | 0 |

### Analysis

- The fastest scenario was `search_api`, which stayed near `0.21-0.24 ms` across all three load levels.
- The highest measured average was on `home_page` under expected load at `2.50 ms`, driven by a warm-up outlier (`40.72 ms max`) rather than sustained slowdown.
- Among the business-heavy authenticated flows, `profile_page` remained the heaviest route at `1.51 ms` average and `1.88 ms` p95 under expected load.
- `recommend_api` was the next-heaviest backend path, which is consistent with recommendation scoring and cache access.
- No scenario produced errors, so experimental availability under the deterministic load model was `100%`.
- The main bottleneck candidate is still profile aggregation because it combines user lookup, recommendation building, and history assembly in one request.

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
| Search API | 500 | no | 200 | 0.64 ms |
| Recommend API | 500 | no | 200 | 29.18 ms |
| Product page | 500 | no | 200 | 32.20 ms |
| Profile page | 302 | yes | 200 | 17.26 ms |
| Admin rebuild | 200 | yes | 200 | 4.21 ms |

### Chaos Metrics

- Fault scenarios executed: `5`
- Graceful degradation cases: `2 / 5`
- Successful recovery after fault removal: `5 / 5`
- Average recovery time: `16.70 ms`

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
venv\Scripts\python.exe scripts\experimental_database.py
venv\Scripts\python.exe scripts\experimental_database_live.py
venv\Scripts\python.exe scripts\experimental_mutation.py
venv\Scripts\python.exe scripts\experimental_chaos.py
```

### Evidence Index

- `docs/experimental_evidence/database_integrity_results.csv`
- `docs/experimental_evidence/database_query_results.csv`
- `docs/experimental_evidence/database_index_results.csv`
- `docs/experimental_evidence/database_results.json`
- `docs/experimental_evidence/database_run.txt`
- `docs/experimental_evidence/database_live_integrity_results.csv`
- `docs/experimental_evidence/database_live_query_results.csv`
- `docs/experimental_evidence/database_live_index_results.csv`
- `docs/experimental_evidence/database_live_results.json`
- `docs/experimental_evidence/database_live_run.txt`
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
