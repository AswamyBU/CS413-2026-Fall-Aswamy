# AI Transcript

## Tool

Claude Code (Anthropic's CLI assistant), model Claude Opus 5.5.

## Prompts

1. > Go through assign03.md and LAMBDA-UI-informal-requirements.md, and give me a concise summary as to what I need to do.

   I used this to get a checklist of the deliverables and the main needs in
   the brief before starting.

2. > Using assign03.md and LAMBDA-UI-informal-requirements.md, please complete requirements.md to the stakeholder's specificaitons

   Claude wrote the full first draft of `REQUIREMENTS.md`. Before writing, it
   also looked at my Assignment 2 interpreter (`lambda0.py`) to see which values
   LAMBDA currently has (ints, bools, strings, pairs).

3. > Look at the requirements file and make sure it's all in line with the instructions for the homework from assign03.md, as well as the AI-Transcript file too and make sure I hit all criteria

   Claude checked both files against the assignment's criteria and fixed the
   problems it found (see below).

## What the AI suggested

- **Keeping the compiler outside the system boundary.** Requirements that
  depend on the compiler (error locations, ASTs) are conditional, e.g. "when
  the compiler reports a location…", instead of making demands on a separate
  project.
- **Using a logical compiler interface** (request/response/cancel) and leaving
  the transport (CLI vs. server vs. Python) as an open question.
- **Dropping a separate "program input" field.** "Change its input" in the
  brief is ambiguous, so it's a clarification question (Q3) with an assumption.
- **Splitting test results into Passed / Failed / Could not complete,** so a
  timeout isn't counted as a compiler bug.
- **Making sharing a low-priority file export** instead of a v1 feature, since
  the instructor said it could wait.
- **Labeling every number it made up** (10 s time limit, 200 ms response,
  etc.) as a proposal, not as something the instructor asked for.

## Corrections and caveats

- Claude pointed out that no stakeholder answers had been received, so all
  eight questions are marked as assumed or unresolved rather than answered.
- Claude told me that three of the review notes in §12 (the original 1, 2
  and 6) were typical draft problems, not issues it had actually run into,
  since it wrote the document in one pass.
- When Claude checked the draft against the assignment, it found real
  problems instead: two wrong cross-references (Q2 and Q6), FR-2 not saying
  what happens to unsaved edits when you switch examples, and QR-1 using a
  "reference machine" that was never defined. These were fixed and replaced
  the three review notes that weren't real.

## How I reviewed it

- I went through the traceability table and checked the rows against the
  paragraphs of the brief they cite, to make sure each requirement actually
  came from something the instructor asked for (or a stated assumption).
- I read through the acceptance criteria to make sure each one had a clear
  starting point, action, and result that someone could actually check.
