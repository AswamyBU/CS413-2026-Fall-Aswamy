# TESTING

Run from `assigns/09`:

```bash
MySolution/.venv/Scripts/python -m unittest discover -s MySolution/tests -t MySolution -v
node --test "MySolution/tests/js/*.test.mjs"
```

**Observed (2026-11-23, Windows 11, Python 3.14.0, Flask 3.1.3, Node 24.11.1):**

| Suite | Result |
| --- | --- |
| Python `unittest` | `Ran 52 tests … OK` (about 6 s) |
| Node `--test` | `tests 12, pass 12, fail 0` |

All database tests go through Flask's HTTP test client and create their data
through the public API. `tests/helpers.Api` validates **every** response body
against `openapi.json`. It also checks that `ETag` equals the returned
revision, that error bodies use the documented envelope with
`application/json`, and that `204` responses are empty.

The only test doubles are:
- an injected clock (for timestamps and cursor expiry);
- a `SlowStore` that delays writes, to widen race windows in the
  concurrency tests;
- a `BrokenStore` that raises, to test the 500 response.

The integration test uses the real LAMBDA3 service.

## Required behaviors → tests

Tests are in `tests/test_api.py` unless noted.

| # | Behavior | Tests | Observed |
| --- | --- | --- | --- |
| 1 | Health, content types, malformed/invalid requests | `HealthAndTransportTests`: `test_health`, `test_unknown_route_is_404_json`, `test_known_route_wrong_method_is_405_with_allow`, `test_unsupported_media_type_is_415`, `test_malformed_json_and_non_object_bodies_are_400`, `test_oversized_body_is_413`, `test_internal_errors_do_not_leak_details`, `test_database_service_never_imports_lambda3` | pass |
| 2 | CRUD for programs and collections | `ProgramCrudTests` (`test_create_get_update_delete`, `test_description_may_be_omitted_or_empty`, `test_list_returns_full_representations_in_creation_order`, `test_timestamps_are_utc_iso8601`); `CollectionAndCaseTests.test_collection_create_get_update_delete`, `test_collection_put_changes_metadata_only` | pass |
| 3 | Add/update/delete/ordered retrieval of cases | `CollectionAndCaseTests.test_add_update_delete_cases_in_order`, `test_unknown_case_id_is_404` | pass |
| 4 | Missing, wrong-type, blank, oversized, and unknown fields | `ValidationTests`: `test_missing_fields`, `test_wrong_types`, `test_blank_fields`, `test_oversized_fields_report_limit_and_actual`, `test_unknown_fields_rejected`, `test_expected_must_match_one_shape`, `test_failed_validation_changes_nothing` | pass |
| 5 | Duplicate names, unknown IDs, page/cursor boundaries | `UniquenessAndIdTests` (all five tests); `PaginationTests`: `test_default_and_bounded_page_size`, `test_invalid_page_parameters`, `test_pages_cover_everything_in_order_without_overlap`, `test_empty_list`, `test_cursor_chain_is_a_stable_snapshot`, `test_collection_cursor_snapshots_cases_too`, `test_cursor_is_bound_to_its_kind`, `test_cursor_expires_after_idle_lifetime`, `test_least_recently_used_snapshot_is_evicted` | pass |
| 6 | Revision increments, stale update/delete conflicts, no partial mutation | `RevisionTests`: `test_missing_if_match_is_428_on_every_mutation`, `test_malformed_if_match_is_400`, `test_each_update_increments_revision_by_one`, `test_stale_update_is_409_and_leaves_record_unchanged`, `test_stale_delete_is_409_and_record_remains`, `test_case_mutations_use_and_bump_collection_revision`, `test_stale_check_comes_after_404_and_428_and_validation`; `CapacityTests.test_capacity_limits_are_409_and_change_nothing`; `ValidationTests.test_failed_validation_changes_nothing`; `UniquenessAndIdTests.test_rename_into_duplicate_is_409_and_changes_nothing` | pass |
| 7 | Atomic concurrent updates: exactly one of two same-revision updates wins | `ConcurrencyTests`: `test_exactly_one_of_two_same_revision_updates_wins` (10 rounds, statuses always `[200, 409]`, final revision 2), `test_concurrent_case_adds_with_same_revision` (`[201, 409, 409]`), `test_concurrent_creates_with_same_name` (`[201, 409, 409, 409]`) | pass |
| 8 | Deleting a collection removes its cases; deleting a program leaves case snapshots | `DeletionTests.test_deleting_collection_removes_its_cases`, `test_deleting_or_editing_program_leaves_case_snapshots` | pass |
| 9 | Studio-level integration: save/reload a program, create and run a collection through LAMBDA3, report an expected success and an expected error | `tests/test_integration.py`: `test_save_reload_and_run_collection_through_lambda3` runs `tests/js/integration.mjs` (real server, real LAMBDA3, real studio modules), and `test_studio_page_and_modules_are_served` | pass. Report: factorial `value 720` PASS, `1 +` syntax error PASS, `1 + true` type error PASS, a wrong expectation FAIL, and a runtime error expecting a syntax error FAIL. **3 passed, 2 failed**, as designed. The stale save returned `409` with `current_revision: 2` |

### Studio client unit tests (`tests/js/studio.test.mjs`)

| Area | Tests |
| --- | --- |
| Storage adapter | `create sends JSON, no If-Match`, `updates and deletes send the revision as a quoted If-Match`, `list builds the query and maps next_cursor`, `API errors become ApiError with code and details`, `network failures become NetworkError` |
| LAMBDA3 client | `success and error codes map to outcome statuses` (-32010 → syntax, -32011 → type, -32012 timeout, -32013 runtime, others → service error), `sends lambda.interpret and reports transport failures` |
| Comparison | `value expectations need success and an exactly equal value`, `error expectations match only their own category` (timeout, runtime, transport, and service errors never match) |
| Runner | `one failure does not stop the remaining cases` (including a thrown error), `results keep the case ID and source snapshot even if the collection is edited mid-run` |
| Drafts | `dirty tracking and case conversion` |

## Studio workflows in a browser

I ran `MySolution/.venv/Scripts/python MySolution/run.py`, opened the studio
in a browser, and drove it with real clicks and typing. A few steps used
scripted DOM events. Observed on 2026-11-23:

| Flow | Steps | Observed |
| --- | --- | --- |
| Start | Load the page | ✔ "database: connected" and "LAMBDA3: connected"; the memory-only warning is shown |
| 1. Create, open, edit, save a program | **New**; type a name and the factorial source; **Run with LAMBDA3**; **Save** | ✔ "● Unsaved changes" shown before saving; run gave `720 : sint`; saved as revision 1 and listed; badge cleared |
| 2. Stale revision | Another client PUTs revision 2 (`fact(5)`); the tab edits to `fact(7)`; **Save** | ✔ Red panel: "Not saved: the server has a newer revision (2)…" with the server's source shown; the form kept `fact(7)`; the server still had revision 2 with `fact(5)` (ETag `"2"`). **Reload server copy** loaded revision 2, cleared the badge, and hid the panel |
| 3. Collections and cases | **New** collection; **Add case** ×5 (value 720, syntax, type, wrong value 999, and one to delete); **Edit** case 4; **Delete** case 5; **Reload from server** | ✔ Case badge "● Unsaved changes" while editing; after reload there were 4 cases in order, the edited description kept, and revision 8 (= 1 + 5 adds + 1 edit + 1 delete) |
| 4. Run collection | **Run collection** | ✔ "Run of revision 8: 3 passed, 1 failed (of 4)": six factorial PASS (value 720), missing operand PASS (syntax error), int plus bool PASS (type error), wrong on purpose FAIL ("expected 999, got 6") |
| Result labels after an edit | Edit case 1's source after the run | ✔ Its result is marked "edited since run" |
| Network failure | Make `fetch` fail; **Refresh lists** | ✔ Banner: "Cannot reach the database service … Is the service running?"; status pill shows "database: unreachable" |
| 5. Persistence and its limit | Reload the page; then restart the service | ✔ After the page reload, the program and collection are still listed. After the service restart, `GET /programs` and `GET /collections` return `{"items": [], "next_cursor": null}` |
