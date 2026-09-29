# Assignment #3
Turning Informal Requirements into a Requirements Specification

## Due date

Tuesday, the 29th of September, 2026

## Objective

Practice requirements engineering by turning an informal stakeholder brief
into a clear, organized, and verifiable requirements specification.

The proposed system is a web-based environment for writing LAMBDA programs,
trying them with a compiler, inspecting results, and keeping examples as tests.
Your task is to determine and specify what this system should do. You are not
required to implement the UI, compiler, or any other software.

## Starting point

Read the [informal stakeholder brief](LAMBDA-UI-informal-requirements.md).
It describes the instructor's needs in ordinary language. It intentionally
leaves some details unclear or unresolved, as stakeholder descriptions often do.

Use this brief as your source material. Do not simply rewrite every sentence
using “shall.” Analyze the needs, identify missing information, resolve or
record ambiguities, and organize the resulting requirements so that another
person could use them to develop and evaluate the system.

## Tasks

### 1. Identify stakeholders and scope

Describe the intended users and their main goals. Define the system boundary,
what belongs in the first version, and what should be outside its scope.
Distinguish the testing environment from the compiler it will use.

### 2. Identify questions and assumptions

Write five to eight clarification questions you would ask the stakeholder.
For each question, explain why the answer matters to the requirements.

Record any stakeholder answers you receive. If an answer is unavailable,
explicitly state any assumption you use to proceed, or mark the issue as
unresolved. Do not present an invented answer as a stakeholder decision.

### 3. Write the requirements specification

Create `MySolution/REQUIREMENTS.md`. Include:

- Purpose, stakeholders, and scope.
- Approximately 12–20 functional requirements describing system behavior.
- Approximately 3–5 quality requirements, such as usability, reliability,
  or responsiveness.
- Relevant external interfaces and dependencies, including the compiler.
- Priorities, assumptions, and unresolved questions.

Give each requirement a unique identifier. Requirements should be clear,
consistent, individually testable, and expressed at an appropriate level of
detail. Avoid vague terms such as “fast” or “easy to use” unless you explain
how their satisfaction could be assessed. If you propose a measurable target
that the brief does not supply, identify it as a proposal or assumption.

Describe required behavior rather than choosing frameworks, programming
languages, or internal algorithms unnecessarily. Separate essential needs
from optional features and explain your priorities. The suggested requirement
counts are a guide; do not split or combine requirements merely to reach a count.

### 4. Define acceptance criteria

For at least six important requirements, describe a concrete scenario or check
that could establish whether the requirement is satisfied. Include at least
two failure or exceptional scenarios.

Each check should identify the requirement, relevant starting conditions,
action or input, and observable expected result. You are specifying future
checks, not reporting results from an implemented system.

### 5. Provide traceability and review

Include a table connecting each requirement to a passage or section of the
brief, a recorded stakeholder answer, or an explicit assumption. A requirement
may have more than one source.

Review your specification for contradictions, missing behavior, ambiguous
wording, and requirements that cannot be verified. Briefly record at least
three issues you found in your draft and how you addressed them.

## Submission

Keep all submitted files under `MySolution/`:

- `REQUIREMENTS.md`: your specification, clarification questions and any
  answers, assumptions, acceptance criteria, traceability table, and review
  notes. These may be sections of a single document.
- `AI-TRANSCRIPT.md`: if you use AI, record the tool, important prompts,
  significant suggestions or corrections, and how you reviewed the output.
  If you do not use AI, state that here.

Aim for roughly 4–6 pages of content, using tables where helpful. Clear
reasoning and useful requirements matter more than document length. No source
code, working prototype, or executed software tests are required.

## Evaluation

| Criterion | Weight |
| --- | --- |
| Coverage of stakeholder needs and appropriate scope | 25% |
| Clarity, consistency, and verifiability of requirements | 30% |
| Clarification questions and treatment of assumptions | 20% |
| Acceptance criteria and traceability | 20% |
| Organization and readability | 5% |

There is no single correct wording or decomposition of the requirements.
Your decisions should be supported by the brief, stakeholder clarification,
or clearly identified assumptions. You are responsible for reviewing and
justifying your submission, including any AI-assisted work.
