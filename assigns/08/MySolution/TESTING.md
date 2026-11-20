# TESTING

Run from `assigns/08`:

```bash
python -m unittest discover -s MySolution/tests -t MySolution -v
node --test "MySolution/tests/js/*.test.mjs"
```

**Observed (2026-11-15, Windows 11, Python 3.14.0, Node 24.11.1):**
Python: `Ran 58 tests ... OK (skipped=1)` in about 13 s. Node: `tests 14, pass 14, fail 0`.
The skipped test (`test_full_8x8_with_interpreter`, run with
`QUEENS_SLOW_TESTS=1`) also passed: the full 8×8 trace through the LAMBDA3
interpreter equals the compiled trace (about 21 s).

Every solver test executes `queens/queens.lam`, either with the LAMBDA3
interpreter, with LAMBDA3's compiler, or with both. Python never reimplements
the search.

## Requirement → tests

| # | Requirement | Tests (file › class › test) | Observed |
| --- | --- | --- | --- |
| 1 | Safety: same line, both diagonals, safe | `test_solver › SafetyTests › test_same_column`, `test_diagonal_up_left`, `test_diagonal_up_right`, `test_safe_placement`, `test_first_queen_on_row_cannot_share_its_row`, `test_check_safe_stops_at_first_conflict` | pass |
| 2 | CPS success/failure, resume at next candidate | `test_solver › CpsTests › test_success_continuation_gets_board_and_resume`, `test_failure_resumes_at_next_candidate`, `test_exhausted_row_calls_enclosing_failure_continuation`, `test_answer_type_is_a_stream_not_a_board` | pass |
| 3 | 92 solutions, deterministic order, no duplicates | `test_solver › SolutionTests › test_92_distinct_solutions_in_lexicographic_dfs_order` (compared with a brute-force oracle), `test_deterministic`, `test_other_sizes_match_oracle` (4→2, 5→10, 6→4, 7→40), `test_interpreter_and_compiler_agree` | 92 distinct, lexicographic |
| 4 | Every event kind, coordinates, snapshots | `test_solver › EventTests › test_every_kind_appears`, `test_board_snapshots_and_coordinates` (replays all 33,589 events), `test_place_only_when_safe`, `test_json_encoding`; `SolutionTests › test_done_once_and_last` | pass |
| 5 | Laziness | `test_solver › LazinessTests › test_constructing_stream_runs_no_thunk_and_no_search` (thunk counter = 0; interpreter trace hook: 0 calls to `try_column` and `check_safe`), `test_forcing_one_cell_leaves_tail_unforced` (head forced, tail `evaluated == False`, exactly 1 `try_column` call and 0 `check_safe` calls), `test_bounded_prefix_does_bounded_work` (10×10: 5 events = 10 thunks, 37 events = 74 thunks), `test_delayed_failure_in_root_continuation_is_never_reached_early` (a root continuation that divides by zero runs only when the event after the last backtrack is requested), `test_large_board_prefix_is_fast`; `test_service › test_open_does_not_force`, `test_next_forces_only_what_is_requested`, `test_next_params` (invalid calls force nothing) | pass |
| 6 | Exhaustion, repeat next, close, unknown, cleanup, expiry | `test_service › StreamLifecycleTests › test_exhaustion_repeated_next_and_release`, `test_done_response_is_short_when_stream_ends`, `test_close_then_unknown`, `test_unknown_id`, `test_expiration_after_idle_ttl` (fake clock), `test_cleanup_sweeps_idle_and_exhausted_records`, `test_open_stream_cap`, `test_streams_are_independent` | pass |
| 7 | IDs, malformed envelopes, unknown methods, invalid params, notifications, app errors | `test_service › EnvelopeTests` (all), `ValidationTests` (all); `test_http › test_notification_gets_204_and_empty_body`, `test_jsonrpc_errors_use_http_200`, `test_transport_errors` | pass |
| 8 | `limit` 1 and 32, never more than requested | `test_service › test_limits_1_and_32`, `test_done_response_is_short_when_stream_ends`, `test_next_params` (0, 33 rejected); `test_http › test_full_8x8_flow_open_to_done` (asserts ≤ 32 on each call) | pass |
| 9 | HTTP flow through all 92 solutions to done | `test_http › HttpTests › test_full_8x8_flow_open_to_done`: real server on an ephemeral port; 33,589 events, 92 distinct solutions, first `[0,4,7,5,2,6,1,3]`, last `[7,3,0,2,5,1,6,4]`, then `done: true`, an empty repeat, close, and `-32001`. Also `test_concurrent_clients_on_one_stream_get_disjoint_events` | pass |
| 10 | Browser controls & failure handling | Node: `tests/js/client.test.mjs` covers start, step batching, play/pause, run to completion, next solution, reset/restart, RPC and transport failures, and the reducer and cell states. DOM: manual checklist below | pass |

## Browser checklist (manual, plus scripted in the in-app browser)

Start the server with `python MySolution/run.py` and open http://127.0.0.1:8000/.
Results observed on 2026-11-15:

| Step | Expected | Observed |
| --- | --- | --- |
| Load page | Empty 8×8 board, "Press Start…", only Start enabled | ✔ |
| **Start** | "Ready…"; Step, Play, Next solution, and Reset enabled; 0 events | ✔ |
| **Step** ×4 | Queen at (0,0); "?" try at row 1; then red ✕ reject with orange outline on the attacking queen; log lines in colour | ✔ |
| **Next solution** | Gold queens `[0,4,7,5,2,6,1,3]`, "Solution #1 found.", 1,858 events, 59 `queens.next` requests and only 6 events buffered, so nothing was prefetched | ✔ |
| **Play**, then **Pause** after about 1 s at 200 ms | About 6 events advance; label switches Play↔Pause; events stop after Pause | ✔ |
| Stream closed behind the page, then **Step** | Red banner: "stream expired or was closed… Press Restart."; status "Stopped by an error." | ✔ |
| **Restart**, then Next solution to the end | 93 presses: 92 solutions, 33,589 events, "Search complete: 92 solutions, no more remain." (green); Step/Play disabled; **Restart search** button shown | ✔ |
| **Restart search** | Fresh stream, 0 solutions | ✔ |
| Network down (fetch rejected), then **Step** | Banner "Network error: Failed to fetch" | ✔ |
| **Reset** | Board cleared, Start label returns, banner hidden, stream closed | ✔ |
| Board size 4, Next solution ×3 | `[1,3,0,2]`, `[2,0,3,1]`, then complete with 2 solutions | ✔ (matches `test_other_sizes_match_oracle`) |
