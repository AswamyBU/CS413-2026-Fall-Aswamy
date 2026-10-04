"""Task 4.4 (and state rules for 4.5/4.6): the model alone, no browser or server."""

import pytest

from contract import Artifact, OpResult, Operation, Status
from model import MAX_SOURCE_BYTES, Rejected, WorkbenchModel


def ok(op, rev, artifact=None):
    return OpResult(op, rev, Status.OK, "fine", "", artifact)


def enabled(m, op):
    return m.action_state(op)[0]


def test_initial_state_has_no_source_and_no_actions():
    m = WorkbenchModel()
    assert m.source is None and m.revision == 0
    assert not any(enabled(m, op) for op in Operation)


def test_manual_input_without_upload():
    m = WorkbenchModel()
    m.start_manual()
    m.edit('D0Eint(7)')
    assert m.dirty and not enabled(m, Operation.LINT)
    m.apply()
    assert m.source.name == "Manual input" and m.source.text == "D0Eint(7)"
    assert m.revision == 1 and not m.dirty
    assert enabled(m, Operation.LINT) and enabled(m, Operation.INTERPRET)


def test_replacement_and_editing_create_new_revisions_and_clear_results():
    m = WorkbenchModel()
    m.load("Factorial", "D0Eint(1)")
    m.begin(Operation.LINT)
    m.finish(ok(Operation.LINT, 1))
    assert len(m.results) == 1
    m.load("Fibonacci", "D0Eint(2)")
    assert (m.source.name, m.revision, m.results) == ("Fibonacci", 2, [])
    m.edit("D0Eint(3)")
    m.apply()
    assert (m.source.name, m.source.text, m.revision) == ("Fibonacci", "D0Eint(3)", 3)


def test_unapplied_edits_block_actions_and_replacement():
    m = WorkbenchModel()
    m.load("a", "D0Eint(1)")
    m.edit("D0Eint(2)")
    with pytest.raises(Rejected, match="unapplied"):
        m.load("b", "D0Eint(9)")
    with pytest.raises(Rejected, match="unapplied"):
        m.start_manual()
    with pytest.raises(Rejected, match="Apply or discard"):
        m.begin(Operation.LINT)
    m.discard()
    assert m.draft_text == "D0Eint(1)" and not m.dirty
    m.begin(Operation.LINT)


@pytest.mark.parametrize("bad", ["", "   \n\t  ", "x" * (MAX_SOURCE_BYTES + 1)],
                         ids=["empty", "whitespace", "too-large"])
def test_rejected_edit_keeps_applied_source_and_draft(bad):
    m = WorkbenchModel()
    m.load("good", "D0Eint(1)")
    m.edit(bad)
    with pytest.raises(Rejected):
        m.apply()
    assert m.source.text == "D0Eint(1)" and m.revision == 1
    assert m.draft_text == bad          # kept for correction
    m.edit("D0Eint(5)")
    m.apply()
    assert m.revision == 2


def test_rejected_uploads_keep_applied_source():
    m = WorkbenchModel()
    m.load("good", "D0Eint(1)")
    for data in [b"\xff\xfe\x00bad", b"   ", b"x" * (MAX_SOURCE_BYTES + 1)]:
        with pytest.raises(Rejected):
            m.load_upload("bad.lambda", data)
        assert (m.source.name, m.revision) == ("good", 1)
    m.load_upload("ok.lambda", "﻿D0Eint(2)".encode("utf-8"))  # BOM tolerated
    assert m.source.text == "D0Eint(2)" and m.revision == 2


def test_busy_blocks_everything_until_finish():
    m = WorkbenchModel()
    m.load("a", "D0Eint(1)")
    m.begin(Operation.INTERPRET)
    assert not any(enabled(m, op) for op in Operation)
    for change in (lambda: m.edit("x"), lambda: m.load("b", "D0Eint(2)"),
                   m.discard, m.start_manual, lambda: m.begin(Operation.LINT)):
        with pytest.raises(Rejected):
            change()
    m.finish(OpResult(Operation.INTERPRET, 1, Status.BACKEND_FAILURE, "boom"))
    assert m.busy is None and m.source.text == "D0Eint(1)"
    assert enabled(m, Operation.INTERPRET)   # retry allowed


def test_stale_result_is_dropped():
    m = WorkbenchModel()
    m.load("a", "D0Eint(1)")
    m.begin(Operation.LINT)
    m.finish(ok(Operation.LINT, 99))
    assert m.results == [] and m.busy is None


def test_execute_needs_artifact_for_current_revision():
    m = WorkbenchModel()
    m.load("a", "D0Eint(1)")
    assert not enabled(m, Operation.EXECUTE)
    assert "compilation" in m.action_state(Operation.EXECUTE)[1].lower()
    # Not-implemented compile must not produce an artifact
    m.begin(Operation.COMPILE)
    m.finish(OpResult(Operation.COMPILE, 1, Status.NOT_IMPLEMENTED, "nope"))
    assert m.artifact is None and not enabled(m, Operation.EXECUTE)
    # Extension path: a real compile result enables Execute ...
    m.begin(Operation.COMPILE)
    m.finish(ok(Operation.COMPILE, 1, Artifact(1, "python", "print(1)")))
    assert enabled(m, Operation.EXECUTE)
    # ... a failed recompile invalidates it ...
    m.begin(Operation.COMPILE)
    m.finish(OpResult(Operation.COMPILE, 1, Status.LANGUAGE_ERROR, "bad"))
    assert m.artifact is None
    # ... and so does a new revision.
    m.begin(Operation.COMPILE)
    m.finish(ok(Operation.COMPILE, 1, Artifact(1, "python", "print(1)")))
    m.edit("D0Eint(2)")
    m.apply()
    assert m.artifact is None and not enabled(m, Operation.EXECUTE)


def test_snapshot_lists_actions_in_required_order():
    m = WorkbenchModel()
    labels = [a["label"] for a in m.snapshot()["actions"]]
    assert labels == ["Lint", "Interpret", "Type-check", "Compile", "Execute"]
