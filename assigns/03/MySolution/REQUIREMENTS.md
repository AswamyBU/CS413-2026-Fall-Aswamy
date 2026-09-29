# Requirements Specification: LAMBDA Web Testing Environment

*Assignment #3 — CS413, Fall 2026 — Arnav Swamy*
*Source: "Stakeholder Brief: A Web-Based Environment for Testing LAMBDA" (the "brief")*

## 1. Purpose

This document specifies the first version (v1) of a browser-based environment
for writing LAMBDA programs, submitting them to the LAMBDA compiler, inspecting
the results, and keeping programs as repeatable tests. It is intended to be
precise enough for a development team to build the environment and for an
evaluator to check it. It does not specify the LAMBDA compiler itself.

Section references such as **[B: Trying ¶2]** point to a heading and paragraph
of the brief. **[B: Intro]** is the text before the first heading.

## 2. Stakeholders and Goals

| Stakeholder | Main goals |
| --- | --- |
| **Instructor** (client, lecturer) | Demonstrate examples in lecture, switching and editing them quickly; results that are clear when projected; a small, agreed-upon v1. |
| **Student, program writer** | Write, load, and save LAMBDA programs; run them; understand errors, including without prior experience with the compiler. |
| **Student, compiler developer** | Rerun a collection of tests after changing the compiler and see quickly what broke; inspect compiler output such as ASTs or generated code. |
| **Compiler interface provider** | Agree on a stable interface between the environment and the compiler. |
| **Environment development team** | Build the UI before the compiler is ready and connect the real compiler later without a rewrite. |

## 3. Scope

### 3.1 System boundary

The **environment** is the system being specified. It includes the browser user
interface, the local storage of programs and tests, the test runner, and an
**adapter** that talks to a compiler. The **compiler** is an external
dependency developed by a separate project [B: Evolving ¶1, ¶2]. The environment
**displays** what the compiler reports (values, errors, locations, ASTs); it
does not **decide** whether a program is correct. Requirements here are written
so that they can be met by any compiler that implements the interface in §7.1.

### 3.2 In scope for v1

Editing programs; built-in examples; loading from and saving to files;
compile-only and run actions; display of values, compile errors, runtime
errors, and environment errors; optional inspection of compiler artifacts;
cancellation and time limits; named test collections with a summary report;
persistence across refreshes and sessions; a clearly labeled sample-response
(mock) compiler; local installation on a single computer.

### 3.3 Out of scope for v1

- Public hosting, user accounts, and authentication [B: Manageable ¶1].
- Real-time collaboration or several people editing the same program [B: Manageable ¶1].
- Sharing collections through the environment (deferred; see FR-19) [B: Tests ¶3].
- Full IDE features: autocomplete, debugger, refactoring, version control, visual effects [B: Manageable ¶3].
- Developing, changing, or hosting the LAMBDA compiler or source notation [B: Evolving ¶2].
- Mobile and touch-screen layouts (assumption A7).

## 4. Clarification Questions

**No stakeholder answers had been received when this document was written
(29 Sept 2026).** Each question therefore lists either an explicit assumption
used to proceed or the status **Unresolved**. These assumptions are proposals
and should not be read as stakeholder decisions.

| ID | Question | Why it matters | Status |
| --- | --- | --- | --- |
| Q1 | What will LAMBDA source text look like, and when will the compiler accept text rather than Python-constructed ASTs? | Affects the editor, the examples, error locations, and whether real compilation is possible in v1. The brief says the notation "is still being discussed" [B: Evolving ¶1]. | **Unresolved.** A1 used to proceed. |
| Q2 | What form will the compiler interface take (command-line program, local server, Python library), and which information will it report: error locations? ASTs? generated code? | Determines §7.1 and whether FR-8 and FR-10 can be implemented. | **Unresolved.** A2 used to proceed. |
| Q3 | When you "change its input" to factorial, do you mean editing a value in the program text, or does LAMBDA read separate input? | If programs take input, the environment needs an input field and tests need to store input. | Assumption A3. |
| Q4 | Where should saved work live: only in the browser, or as files the student can copy to another computer? | Browser storage survives refresh but is tied to one browser; files are portable but need explicit saving. Affects FR-3–FR-5. | Assumption A4. |
| Q5 | What can a test expect? Only an integer/Boolean value or "compiler rejects it", or also runtime errors, specific error messages, strings, or pairs? | Defines the test format (FR-15) and when a test passes. | Assumption A5. |
| Q6 | How long should a run take before it is stopped automatically, and should users be able to change the limit? | Needed so a non-terminating test cannot block a collection (FR-13, FR-16). | Assumption A6. |
| Q7 | Which browsers and operating systems must be supported, and what software can setup instructions assume is installed (e.g. Python)? | "A browser students normally use" is not testable as stated [B: Manageable ¶1]. Affects QR-5. | Assumption A7. |
| Q8 | Which examples should be built in, and who updates them as the notation changes? | Lecture use depends on having good examples [B: Trying ¶1]; examples break if notation changes. | Assumption A8; maintenance **Unresolved**. |

### 4.1 Assumptions

| ID | Assumption |
| --- | --- |
| A1 | Programs are entered as plain text. Until a parser exists, the adapter or the mock compiler handles text; the environment makes no assumptions about syntax. |
| A2 | The compiler is reached only through the adapter interface in §7.1. It may or may not report locations and artifacts; the environment must work in either case. |
| A3 | LAMBDA programs take no separate input. "Changing the input" means editing the program text. |
| A4 | Work is saved automatically in the browser's local storage. Import/export to files provides portability and backup. |
| A5 | A test expects either (a) a specific value, compared by the compiler's printed representation (e.g. `120`, `true`), (b) a compile error, or (c) a runtime error. Matching specific error messages is not required in v1. |
| A6 | Proposed default time limit: 10 seconds per run, adjustable by the user from 1 to 300 seconds. |
| A7 | Supported browsers are proposed as the current and previous major versions of Chrome, Firefox, Edge, and Safari on a desktop or laptop. The machine is assumed to have whatever runtime the compiler needs. The **reference machine** used for timing targets (QR-1) is proposed as a laptop no more than five years old with at least 8 GB of memory. |
| A8 | v1 ships at least four examples: factorial, one other recursive function, a program with a compile error, and a non-terminating program (for demonstrating cancellation). |
| A9 | The environment is used by one person at a time on one computer. |

## 5. Functional Requirements

Priority: **M** = Must (essential for v1), **S** = Should (in v1 if time
permits), **C** = Could (defer to a later version unless trivial). The
rationale is given in §8.

### 5.1 Editing and managing programs

| ID | Requirement | Pri. |
| --- | --- | --- |
| FR-1 | The environment shall provide a text editor in which the user can type, paste, and edit a LAMBDA program. The editor shall display line numbers. | M |
| FR-2 | The environment shall provide a list of built-in examples. Selecting an example shall open a **copy** of it in the editor. Editing the copy shall never change the built-in example, and the original shall stay available from the list. If the editor holds unsaved changes when an example is selected, those changes shall be kept as a draft in the workspace rather than discarded. | M |
| FR-3 | The user shall be able to open a program from a file on the local computer into the editor. The file itself shall not be modified. | M |
| FR-4 | The user shall be able to save the current program under a name in the workspace, reopen it later, and export it to a local file. | M |
| FR-5 | The workspace (saved programs, the current editor contents, test collections, and settings) shall be kept automatically and shall still be present after a page refresh or after the browser is closed and reopened. | M |

### 5.2 Compiling and running

| ID | Requirement | Pri. |
| --- | --- | --- |
| FR-6 | The user shall be able to request **Check** (compile only). The environment shall show whether the program compiled without running it. | M |
| FR-7 | The user shall be able to request **Run**. The environment shall show the resulting value as reported by the compiler. | M |
| FR-8 | When the compiler provides artifacts (e.g. an AST or generated code), the user shall be able to view each of them. Artifacts shall be hidden by default and shall not appear unless the user asks for them. When no artifact is available, the environment shall say so rather than show an empty view. | S |

### 5.3 Presenting results

| ID | Requirement | Pri. |
| --- | --- | --- |
| FR-9 | Every result shall be labeled with exactly one of these outcomes, each with a distinct text label: **Compiled OK**, **Value**, **Compilation error**, **Runtime error**, **Cancelled**, **Timed out**, **Environment problem**. Error results shall include the message text supplied by the compiler, unaltered. | M |
| FR-10 | When the compiler reports a source location for an error, the environment shall display it (line and, if given, column) and shall let the user move the editor cursor to that location with one action, which also highlights the line. | M |
| FR-11 | When the compiler cannot be reached, fails to respond, or returns a response the adapter cannot interpret, the environment shall report an **Environment problem** stating that the program was not checked. It shall keep the editor contents unchanged and offer a **Retry** action. | M |

### 5.4 Long-running work

| ID | Requirement | Pri. |
| --- | --- | --- |
| FR-12 | While a Check or Run is in progress, the environment shall show that it is in progress and offer a **Cancel** action. Cancelling shall stop the request and report the outcome **Cancelled**. | M |
| FR-13 | A request that exceeds the time limit (A6) shall be stopped automatically and reported as **Timed out**, showing the limit that was applied. | M |
| FR-14 | Each result shall identify the version of the program that produced it (a revision number plus time submitted). If the editor has changed since that version was submitted, the result shall be marked **Out of date**. Starting a new request cancels any request still in progress from the same editor, and a result from a cancelled request shall never be shown as the current result. | M |

### 5.5 Tests

| ID | Requirement | Pri. |
| --- | --- | --- |
| FR-15 | The user shall be able to create, rename, edit, and delete named tests in a named collection. Each test consists of a name, a program, and an expected outcome as defined in A5. The user shall be able to create a test from the current editor contents. | M |
| FR-16 | The user shall be able to run all tests in a collection, or a selected subset, with one action. Each test shall run separately under the time limit. A test that fails, errors, times out, or causes an environment problem shall not prevent the remaining tests from running. | M |
| FR-17 | After a test run, the environment shall show a summary with counts of **Passed**, **Failed** (wrong outcome), and **Could not complete** (timed out, cancelled, or environment problem), followed by one status line per test. | M |
| FR-18 | For each test that did not pass, the user shall be able to see the expected outcome, the actual outcome, and the compiler's messages, and to open the test's program in the editor. | M |
| FR-19 | The user shall be able to export a collection to a single file and import such a file, keeping test names, programs, and expectations. (This is an easy route for sharing; sharing inside the environment is out of scope.) | C |

### 5.6 Compiler integration

| ID | Requirement | Pri. |
| --- | --- | --- |
| FR-20 | The environment shall be able to run against a **sample-response provider** (mock compiler) that implements the same interface as the real compiler (§7.1). While it is active, every result, and the page header, shall show the non-dismissible label **"SAMPLE RESPONSE — not produced by the LAMBDA compiler"**. Which provider is used shall be chosen by configuration, not by changing interface code. | M |

## 6. Quality Requirements

Numeric targets below are **proposals** (the brief does not give numbers) and
should be confirmed with the instructor.

| ID | Requirement | How it is assessed | Pri. |
| --- | --- | --- | --- |
| QR-1 Responsiveness | Ordinary UI actions (typing, selecting an example, opening a result, pressing Cancel) shall produce a visible response within 200 ms (proposal) on the reference machine, including while a compiler request is running. | Timed trial during a run of the non-terminating example. | M |
| QR-2 Accessibility | Every main task (open example, edit, Check, Run, Cancel, jump to error, run tests, read summary) shall be possible using only the keyboard. Every outcome in FR-9 shall be conveyed by text or an icon with a text label, never by color alone. | Keyboard-only walkthrough; review of screens in grayscale. | M |
| QR-3 Data preservation | No saved program or test shall be lost because of a page refresh, a compiler failure, or an environment problem. Unsaved edits shall be kept automatically within 2 s (proposal) of the last keystroke. | Refresh or close the browser 3 s after an edit; stop the compiler mid-run; check contents afterwards. | M |
| QR-4 Learnability and lecture use | A first-time user with no compiler experience shall be able to open an example and run it within 2 minutes (proposal) without outside help. Switching from one example to another and running it shall take no more than 3 user actions. | Observe 3 users new to the tool; count actions in a scripted demo. | M |
| QR-5 Portability and setup | The environment shall work in the browsers listed in A7. Someone outside the team shall be able to install and start it within 15 minutes (proposal) by following only the written setup instructions. | Setup trial by a volunteer on a clean machine; smoke test in each listed browser. | M |

## 7. External Interfaces and Dependencies

### 7.1 Compiler interface (through the adapter)

The transport (command-line program, local HTTP service, or Python call) is
**unresolved** (Q2). Whatever the transport, the adapter must support the
following logical exchange, so that the UI does not depend on the transport:

- **Request:** request id; program text; action (`check` or `run`); whether artifacts are wanted.
- **Response:** request id; status (`ok`, `compile-error`, `runtime-error`); value as printed text, with a type name if available; a list of diagnostics, each with a message and an **optional** line/column; a list of **optional** artifacts, each with a name (e.g. "AST") and text; an identifier for the compiler version or the mock provider.
- **Cancellation:** the adapter must be able to stop an in-progress request, for example by ending the compiler process.
- **Failure:** a missing, late, or unreadable response is reported to the UI as an environment problem, never as a compile error (FR-11).

### 7.2 Other dependencies

| Dependency | Use |
| --- | --- |
| LAMBDA compiler (separate project) | Produces all values, errors, locations, and artifacts. Currently an interpreter over Python-constructed ASTs, with no source parser [B: Evolving ¶1]. |
| Sample-response provider | Stands in for the compiler before it is ready (FR-20). Must be maintained alongside the examples. |
| Browser local storage | Persistence of the workspace (A4, FR-5). |
| Local file system (via browser file dialogs) | Opening and exporting programs and collections (FR-3, FR-4, FR-19). |
| Supported web browsers (A7) | Runs the user interface. |

## 8. Priorities

**Must** requirements cover what the brief names as most important: "reliable
editing, understandable results, and repeatable tests" [B: Manageable ¶3],
plus the mock compiler, since work must start before the compiler is ready
[B: Evolving ¶2]. **FR-8** (artifacts) is **Should** because it depends on
information the compiler may not provide (Q2), and the brief says "when that
information is available." **FR-19** is **Could** because the instructor said
sharing "could live without that in the first version" [B: Tests ¶3]. IDE
features and visual effects are explicitly deferred [B: Manageable ¶3].

## 9. Acceptance Criteria

These are checks to perform on a future implementation. AC-4, AC-5, and AC-7
are failure or exceptional scenarios.

| ID | Req. | Starting conditions | Action / input | Expected observable result |
| --- | --- | --- | --- | --- |
| AC-1 | FR-2, FR-7 | Fresh workspace. Factorial example computes the factorial of 5. | Select factorial; change 5 to 6; Run. Then select factorial from the example list again. | Result labeled **Value** shows `720`. Reselecting opens a copy that still computes the factorial of 5; the example list entry is unchanged. |
| AC-2 | FR-6, FR-9, FR-10 | Real compiler that reports locations. Program with a syntax error on line 3. | Check; then use the jump-to-error action. | Result labeled **Compilation error** with the compiler's message and "line 3". No value is shown. The cursor moves to line 3 and the line is highlighted. |
| AC-3 | FR-9 | Program that compiles but fails when run (e.g. division by zero). | Run. | Result labeled **Runtime error**, a different label from AC-2, with the compiler's message. |
| AC-4 | FR-11, QR-3 | Compiler process stopped. Editor holds an unsaved, correct program. | Run; then restart the compiler and press Retry. | First: **Environment problem** saying the program was not checked; no "Compilation error" label; editor text unchanged. After Retry: the correct **Value** is shown. |
| AC-5 | FR-12, FR-13, QR-1 | Non-terminating recursive example loaded; time limit 10 s. | (a) Run; type in the editor; press Cancel after 3 s. (b) Run again and wait. | (a) Typing appears within 200 ms while running; **Cancelled** is shown and no value appears. (b) After about 10 s, **Timed out (limit 10 s)** is shown. In both cases another program can then be run. |
| AC-6 | FR-14 | Program that takes ~5 s to run. | Run (revision 1); edit the program during the run (revision 2) without running again. | Result is shown as produced by revision 1 and marked **Out of date**. |
| AC-7 | FR-16, FR-17, FR-18 | Collection with four tests: T1 expects `120` (correct); T2 expects a compile error and the program is rejected; T3 expects `true` but program gives `false`; T4 never terminates. | Run all tests. | All four tests report a status. Summary: **Passed 2, Failed 1, Could not complete 1**. Opening T3 shows expected `true`, actual `false`, and offers to open its program. |
| AC-8 | FR-5, QR-3 | A saved program, a two-test collection, and unsaved edits made 3 s earlier. | Refresh the page; then close and reopen the browser. | After both, the program, the collection, and the edits are all present. |
| AC-9 | FR-20 | Environment configured to use the sample-response provider. | Run factorial; run the test collection. | Page header and each result show **"SAMPLE RESPONSE — not produced by the LAMBDA compiler"**; the label cannot be hidden. |
| AC-10 | QR-2 | Fresh workspace; no mouse. | Using only the keyboard: open an example, Run, open the error location of a broken example, run a collection. | All steps can be completed; each outcome is identifiable from its text label when viewed in grayscale. |

## 10. Traceability

| Req. | Source(s) |
| --- | --- |
| FR-1 | B: Trying ¶1 ("typing or pasting a short program") |
| FR-2 | B: Trying ¶1 (examples; "without losing access to the original"); B: Manageable ¶2 (moving between examples in lectures); A8 |
| FR-3 | B: Trying ¶3 ("programs saved in files … not have to retype") |
| FR-4 | B: Trying ¶3 ("keep a program … return to it later"); A4 |
| FR-5 | B: Tests ¶3 (refresh; another session); A4 |
| FR-6 | B: Trying ¶2 ("only want to check whether a program compiles") |
| FR-7 | B: Trying ¶2 ("run it and see the answer"); A3 |
| FR-8 | B: Trying ¶2 (AST, generated code, "not … get in the way"); A2 |
| FR-9 | B: Understanding ¶1 (useful explanation; compile vs run failure); B: Understanding ¶2 |
| FR-10 | B: Understanding ¶1 ("help the student find that place"); A2 |
| FR-11 | B: Understanding ¶2 (cannot reach compiler; keep work; try again) |
| FR-12 | B: Understanding ¶3 ("a way to stop it"; "remain usable") |
| FR-13 | B: Understanding ¶3 ("might never finish"); B: Tests ¶2 ("one troublesome test"); A6 |
| FR-14 | B: Understanding ¶3 ("which version produced the result") |
| FR-15 | B: Tests ¶1, ¶2 (named tests; expected answer or rejection); A5 |
| FR-16 | B: Tests ¶1 ("run the collection again"); B: Tests ¶2 ("one troublesome test") |
| FR-17 | B: Tests ¶2 ("quick summary") |
| FR-18 | B: Tests ¶2 ("enough detail to investigate") |
| FR-19 | B: Tests ¶3 (sharing optional); A4 |
| FR-20 | B: Evolving ¶2 (sample responses, not mistaken for real; connect real compiler later) |
| QR-1 | B: Understanding ¶3; B: Manageable ¶2 ("respond promptly"); A7 |
| QR-2 | B: Manageable ¶2 (keyboard; not only colors) |
| QR-3 | B: Understanding ¶2; B: Tests ¶3 |
| QR-4 | B: Intro ¶2 ("easy to get started"); B: Manageable ¶2 (lectures) |
| QR-5 | B: Manageable ¶1 (usual browser; straightforward setup); A7 |
| §7.1 | B: Evolving ¶1, ¶2; A1, A2 |

## 11. Unresolved Issues

1. **Source notation and compiler readiness (Q1).** Until resolved, real compilation cannot be tested end to end, and built-in examples may need rewriting.
2. **Compiler interface transport and contents (Q2).** Must be agreed with the interface provider before the adapter is built; FR-8 and FR-10 depend on it.
3. **Maintaining examples and sample responses (Q8).** No owner has been named for keeping them in step with the evolving notation.
4. **All proposed numeric targets** (A6, QR-1, QR-3, QR-4, QR-5) need confirmation from the instructor.

## 12. Review Notes

Issues found while reviewing the draft, and how they were addressed:

1. **Wrong cross-references.** After requirements were merged and renumbered, Q2 pointed to FR-11 (environment problems) instead of FR-10 (error locations), and Q6 pointed to FR-17 (summary) instead of FR-16 (isolating tests). Both references were corrected.
2. **Missing behavior.** FR-2 did not say what happens to unsaved edits when another example is selected, so switching examples during a lecture could silently lose work. FR-2 now keeps those edits as a draft instead of discarding them (without adding a confirmation step, so QR-4's three-action limit still holds).
3. **Unsupported feature.** The draft had a separate "program input" field, based on "change its input." Nothing in the brief says LAMBDA reads input, so this was removed and recorded as Q3 with assumption A3.
4. **Ambiguous test status.** The draft counted a timed-out test as "Failed," which would hide the difference between a compiler bug and a slow or broken test. FR-17 now separates **Failed** from **Could not complete**.
5. **Scope contradiction.** Sharing was listed both in scope and as optional. Following [B: Tests ¶3], in-environment sharing is now out of scope, and file export (FR-19) is a low-priority Could.
6. **Unverifiable target.** QR-1 measured responsiveness "on the reference machine," but no reference machine was defined, so the 200 ms target could not be checked. A7 now proposes one.
