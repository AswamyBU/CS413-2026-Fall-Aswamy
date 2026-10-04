# Testing

## Automated tests

Run from `assigns/04/MySolution` with the virtual environment active (see
README):

```
python -m pytest -q
```

Last result: **97 passed** (Python 3.14.0, Flask 3.1.3, pytest 9.1.1, Windows 11).

| File | What it covers | Assignment Task 4 item |
| --- | --- | --- |
| `tests/test_reader_fvset.py` | `d0exp_fvset` for all 13 constructors (both `if` branches), duplicate occurrences, nested bindings and shadowing, `fix` binding name + parameter, `let` initializer scope, unused bindings, `frozenset` return type. The restricted reader: comments, multiline/indented input, keyword args, and 19 rejected inputs (code injection, wrong literal kinds, bad operators, arity, `*args`, excessive nesting). | 1 |
| `tests/test_backend.py` | Lint passes closed programs and lists free names sorted. Lint does **not** evaluate: a division-by-zero program passes, and a monkeypatched `d0exp_evaluate` that raises is never called. Interpret covers arithmetic, factorial (0, 1, 5, 10), Fibonacci (0, 1, 2, 10), the canned files, malformed input → `INPUT_ERROR`, runtime failures (division by zero, type error, deep recursion) → `LANGUAGE_ERROR`, the `D0V000()` sentinel directly and inside a pair, and timeout → `BACKEND_FAILURE`. Type-check/Compile are `NOT_IMPLEMENTED` and create no artifact. Execute is `UNAVAILABLE` without a current artifact. | 2, 3, 5 |
| `tests/test_model.py` | **Model only, no browser or server.** Manual input without upload, replacement, editing, new revisions clearing results, unapplied edits blocking actions and replacement, rejected empty/whitespace/oversized edits and invalid-UTF-8/oversized uploads preserving the applied source (and the draft for correction), busy blocking all changes, stale results dropped, artifact lifecycle for Execute, button order. | 4, 5, 6 |
| `tests/test_controller.py` | **Controller with substitute backends; view code unchanged.** `RecordingBackend` checks each action dispatches to the matching method and that Execute is never dispatched without an artifact. With the real backend, placeholders never appear as success. Manual edit → apply → Lint error → fix → Lint OK → Interpret 42. `BlockingBackend` shows the busy state is visible and that conflicting actions/edits/loads are rejected while busy, then cleared. `FlakyBackend` raises once → `BACKEND_FAILURE`, source preserved, retry succeeds. Real timeout → edit → retry succeeds. | 4, 5, 6 |
| `tests/test_app.py` | Flask test client: page and assets served, example → Lint → Interpret over HTTP, good and invalid-UTF-8 uploads, draft edit/apply/discard, HTML-like text carried verbatim. **Architectural boundary checks:** `model.py` imports only `contract`; `controller.py` does not import Flask/`lambda1`/`backend`/`reader`; `view.js` has no `innerHTML` and no language logic. | 4, 5 |

## Browser smoke test

Run on 2026-10-03 against `python app.py` (http://127.0.0.1:5000/) in Google
Chrome on Windows 11. I drove the browser with an automation extension
(Claude in Chrome). Typing, keyboard navigation, menu selection, and file
upload went through the real browser input paths. Some button presses were
issued as DOM `click()` calls from a script, which fires the same click
handlers. Observations were read from the rendered page (screenshots and DOM
text).

| # | Steps | Expected | Observed |
| --- | --- | --- | --- |
| B1 | Open the page | Status "Ready."; "No source applied."; all five buttons disabled, each with a reason | As expected |
| B2 | Load source menu → *Factorial (canned)* → Load | "Applied source: Factorial — revision 1"; editor shows the example; Lint–Compile enabled; Execute disabled | As expected |
| B3 | Lint, Interpret, Type-check, Compile | Lint "Success: No free variables found"; Interpret `D0Vint(arg1=3628800)`; "Not implemented: Type checking is not yet implemented"; "Not implemented: Compilation is not yet implemented"; every result tagged "revision 1" | As expected |
| B4 | Inspect Execute after Compile | Execute still disabled; reason "Execute runs generated code from Compile; compilation is not yet implemented, so no artifact exists." | As expected |
| B5 | Click Interpret and watch status | "Busy: running Interpret…" with editor read-only and all buttons disabled, then "Ready." with controls restored | As expected (captured with a DOM MutationObserver) |
| B6 | Menu → *Manual input* → Load, type `D0Evar("x")` on the keyboard | Blank editor; while typing, "Unapplied edits", all actions and the Load menu disabled; Factorial remains the applied source | As expected (screenshot) |
| B7 | Apply changes → Lint | Revision 2, old results cleared; "Lint · revision 2 · Error (program): Undeclared variable(s): x" | As expected |
| B8 | Ctrl+A in editor, type `D0Elet("x", D0Eint(41), D0Eop1("+1", D0Evar("x")))`, Apply, Lint, Interpret | Revision 3; Lint success; Interpret `D0Vint(arg1=42)`; no characters lost while typing | As expected |
| B9 | Enter the division-by-zero `let` program, Apply, Lint, Interpret | Lint success; Interpret "Error (program): Runtime error … division by zero" | As expected |
| B10 | Replace text with spaces only, Apply | "Error: Source is empty or whitespace only."; applied revision unchanged; spaces kept in the editor | As expected |
| B11 | Discard changes | Editor restored to the applied source, "No unapplied edits." | As expected |
| B12 | Enter `D0Epair(D0Evar("<b>bold</b>"), D0Evar("<img src=x onerror=alert(1)>"))`, Apply, Lint, Interpret | Names shown literally as text; no `<b>`/`<img>` elements created; no alert; Interpret reports the `D0V000()` sentinel as an error | As expected (0 `b`/`img` elements in results) |
| B13 | Change Fibonacci argument to 40, Apply, Interpret | Busy during the run; after ~5 s "Failure (backend): Interpretation timed out … Stopped after 5 s"; controls restored; source unchanged | As expected (screenshot) |
| B14 | Retry: edit 40 → 20, Apply, Interpret | `D0Vint(arg1=6765)` | As expected |
| B15 | Choose File: upload `examples/factorial.lambda` | "Applied source: factorial.lambda — revision 9" | As expected |
| B16 | Choose File: upload `examples/invalid_utf8.lambda` | "Error: File is not valid UTF-8 text (byte 9)."; factorial.lambda still applied | As expected |
| B17 | Keyboard only: focus the menu, ArrowDown to *Factorial*, Tab to Load, Enter; Tab to Lint, Enter; Tab to Interpret, Enter | Each control activates; focus stays on the control just used | **First run failed:** focus fell back to `<body>` after each request because controls were disabled while busy and action buttons were rebuilt on every render. **Fixed** (stable buttons + focus restore in `view.js`); re-run passed: focus stayed on Load, then Lint, then Interpret; Interpret showed `D0Vint(arg1=3628800)` |

One harness note: during one long scripted run (B13–B14 combined in a single
script), the automation tool's 45 s evaluation limit expired and the tab
stopped updating briefly. The server log showed every request completing
normally, and the page showed the correct final state once the script was
released. B13 was then repeated in shorter steps.

## Traceability to F1–F10

| Req | Automated tests | Browser checks |
| --- | --- | --- |
| F1 Load menu, upload, manual, canned, name + revision | `test_model::test_manual_input_without_upload`, `test_replacement_and_editing…`; `test_app::test_example_lint_interpret_over_http`, `test_upload_good_and_bad_files` | B2, B6, B15, B17 |
| F2 Typing/editing, Apply/Discard, edits block actions and replacement | `test_model::test_unapplied_edits_block_actions_and_replacement`; `test_app::test_draft_edit_apply_discard_over_http` | B6, B8, B11 |
| F3 Reject empty/whitespace, invalid UTF-8, > 64 KiB; keep applied source and draft | `test_model::test_rejected_edit_keeps_applied_source_and_draft`, `test_rejected_uploads_keep_applied_source` | B10, B16 |
| F4 Button order, applied source required, Execute disabled | `test_model::test_snapshot_lists_actions_in_required_order`, `test_initial_state…`, `test_execute_needs_artifact…` | B1, B3, B4 |
| F5 Real Lint | `test_reader_fvset.py` (all), `test_backend::test_lint_*` | B7, B8, B9 |
| F6 Real Interpret, input vs runtime errors | `test_backend::test_interpret_*` | B3, B8, B9, B12 |
| F7 Placeholders and Execute explanation | `test_backend::test_typecheck_and_compile_are_not_implemented`, `test_execute_without_artifact…`; `test_controller::test_placeholders_never_look_successful…`, `test_execute_is_not_dispatched…` | B3, B4 |
| F8 New revision clears results/artifacts; rejections preserve state | `test_model::test_replacement_and_editing…`, `test_execute_needs_artifact…`, rejection tests | B7, B10, B16 |
| F9 Results show action, revision, outcome; literal text | `test_app::test_draft_edit_apply_discard_over_http`, `test_view_renders_text_literally…` | B3, B12 |
| F10 Busy status, conflicts prevented, recovery and retry | `test_model::test_busy_blocks_everything_until_finish`, `test_stale_result_is_dropped`; `test_controller::test_busy_state…`, `test_backend_exception…`, `test_timeout_then_edit_and_retry…`; `test_backend::test_interpret_timeout…` | B5, B13, B14 |
