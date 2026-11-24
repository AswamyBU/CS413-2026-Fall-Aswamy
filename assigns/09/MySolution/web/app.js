// LAMBDA Studio UI. DOM and workflow only: all REST details live in
// storage.js, all JSON-RPC details in lambda.js, and run/compare logic in
// runner.js. Records always carry `revision`; the adapter turns it into
// If-Match, so a stale save becomes an ApiError with code revision_conflict.

import { ApiError, NetworkError, createStorage } from "./storage.js";
import { createLambdaClient } from "./lambda.js";
import { describeExpected, describeOutcome, resultIsStale, runCollection } from "./runner.js";
import { caseDraft, caseFromDraft, collectionDraft, isDirty, programDraft } from "./drafts.js";

const store = createStorage({ baseUrl: "/api/v1" });
const lambda = createLambdaClient({ url: "/lambda/rpc" });
const $ = (id) => document.getElementById(id);
const PAGE = 20;

const state = {
  programs: [], programsCursor: null,
  collections: [], collectionsCursor: null,
  program: null,          // saved program record, or null for a new unsaved program
  programOpen: false,
  programBase: programDraft(null),
  collection: null,       // saved collection record (with cases)
  collectionBase: collectionDraft(null),
  caseEditing: undefined, // undefined: form closed; null: new case; string: case id
  caseBase: caseDraft(null),
  run: null,              // last run result for the open collection
  running: false,
  lambdaUp: false,
};

// ------------------------------------------------------------ feedback

function notify(message, kind = "error") {
  const box = $("notice");
  box.textContent = message;
  box.className = `notice ${kind === "info" ? "info" : ""}`;
  box.hidden = false;
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => { box.hidden = true; }, kind === "info" ? 3000 : 8000);
}

function explain(err) {
  if (err instanceof NetworkError) return `${err.message}. Is the service running?`;
  if (err instanceof ApiError) return `${err.message} (${err.status} ${err.code})`;
  return String(err?.message ?? err);
}

// Show a validation error next to the form and outline the offending input.
function showFieldError(prefix, err, fieldInputs) {
  const p = $(`${prefix}-error`);
  for (const el of Object.values(fieldInputs)) el?.classList.remove("invalid");
  if (!err) { p.hidden = true; return; }
  p.textContent = explain(err);
  p.hidden = false;
  const field = err instanceof ApiError ? (err.details.field ?? "").split(".")[0] : "";
  fieldInputs[field]?.classList.add("invalid");
}

const fmtTime = (iso) => new Date(iso).toLocaleString();

// ------------------------------------------------------------ dirty tracking

function readProgramForm() {
  return { name: $("program-name").value, description: $("program-description").value, source: $("program-source").value };
}
function readCollectionForm() {
  return { name: $("collection-name").value, description: $("collection-description").value };
}
function readCaseForm() {
  return {
    name: $("case-name").value, source: $("case-source").value, description: $("case-description").value,
    kind: document.querySelector("input[name=case-kind]:checked").value,
    value: $("case-value").value, category: $("case-category").value,
  };
}
const programDirty = () => state.programOpen && isDirty(readProgramForm(), state.programBase);
const collectionDirty = () => !!state.collection && isDirty(readCollectionForm(), state.collectionBase);
const caseDirty = () => state.caseEditing !== undefined && isDirty(readCaseForm(), state.caseBase);
const anyDirty = () => programDirty() || collectionDirty() || caseDirty();

function updateDirtyBadges() {
  $("program-dirty").hidden = !programDirty();
  $("collection-dirty").hidden = !collectionDirty();
  $("case-dirty").hidden = !caseDirty();
}

function confirmDiscard(what) {
  return confirm(`You have unsaved changes to ${what}. Discard them?`);
}

window.addEventListener("beforeunload", (event) => {
  if (anyDirty()) { event.preventDefault(); event.returnValue = ""; }
});

// ------------------------------------------------------------ lists

function renderList(listEl, records, activeId, onOpen, emptyText) {
  listEl.innerHTML = "";
  if (!records.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = emptyText;
    listEl.append(li);
    return;
  }
  for (const r of records) {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = r.name;
    b.title = r.description || r.name;
    b.dataset.id = r.id;
    if (r.id === activeId) b.className = "active";
    b.addEventListener("click", () => onOpen(r.id));
    li.append(b);
    listEl.append(li);
  }
}

function renderLists() {
  renderList($("program-list"), state.programs, state.program?.id, openProgram, "No saved programs yet.");
  renderList($("collection-list"), state.collections, state.collection?.id, openCollection, "No collections yet.");
  $("more-programs").hidden = !state.programsCursor;
  $("more-collections").hidden = !state.collectionsCursor;
}

async function loadPrograms(more = false) {
  try {
    const page = await store.listPrograms({ limit: PAGE, cursor: more ? state.programsCursor : undefined });
    state.programs = more ? state.programs.concat(page.items) : page.items;
    state.programsCursor = page.nextCursor;
  } catch (err) {
    if (more && err instanceof ApiError && err.details.parameter === "cursor") return loadPrograms(false);
    notify(`Could not load programs: ${explain(err)}`);
  }
  renderLists();
}

async function loadCollections(more = false) {
  try {
    const page = await store.listCollections({ limit: PAGE, cursor: more ? state.collectionsCursor : undefined });
    state.collections = more ? state.collections.concat(page.items) : page.items;
    state.collectionsCursor = page.nextCursor;
  } catch (err) {
    if (more && err instanceof ApiError && err.details.parameter === "cursor") return loadCollections(false);
    notify(`Could not load collections: ${explain(err)}`);
  }
  renderLists();
}

// ------------------------------------------------------------ program editor

function showPanel(which) {
  $("program-panel").hidden = which !== "program";
  $("collection-panel").hidden = which !== "collection";
  $("empty-panel").hidden = which !== null;
}

function fillProgram(program) {
  state.program = program;
  state.programOpen = true;
  state.programBase = programDraft(program);
  $("program-name").value = state.programBase.name;
  $("program-description").value = state.programBase.description;
  $("program-source").value = state.programBase.source;
  $("program-title").textContent = program ? program.name : "New program";
  $("program-meta").textContent = program
    ? `revision ${program.revision} · saved ${fmtTime(program.updated_at)}`
    : "not saved yet";
  $("delete-program").disabled = !program;
  $("reload-program").disabled = !program;
  $("program-conflict").hidden = true;
  $("program-output").hidden = true;
  showFieldError("program", null, programInputs());
  updateDirtyBadges();
  renderLists();
}

const programInputs = () => ({ name: $("program-name"), source: $("program-source"), description: $("program-description") });

async function openProgram(id) {
  if (programDirty() && !confirmDiscard("this program")) return;
  try {
    const program = await store.getProgram(id);
    fillProgram(program);
    showPanel("program");
  } catch (err) {
    notify(`Could not open program: ${explain(err)}`);
    if (err instanceof ApiError && err.status === 404) loadPrograms();
  }
}

function newProgram() {
  if (programDirty() && !confirmDiscard("this program")) return;
  fillProgram(null);
  showPanel("program");
  $("program-name").focus();
}

function showConflict(kind, err, serverCopy, keepLabel) {
  const box = $(`${kind}-conflict`);
  box.innerHTML = "";
  const title = document.createElement("strong");
  title.textContent = serverCopy
    ? `Not saved: the server has a newer revision (${serverCopy.revision}) than the one you opened.`
    : "Not saved: this record was deleted on the server.";
  const p = document.createElement("p");
  p.textContent = serverCopy
    ? "Someone else saved changes after you loaded this. Your edits are still in the form and were NOT written. Reload the server copy (your edits will be discarded), or keep editing and copy what you need first."
    : "Your edits are still in the form. You can save them as a new record.";
  box.append(title, p);
  if (serverCopy?.source !== undefined) {
    const pre = document.createElement("pre");
    pre.textContent = serverCopy.source;
    const label = document.createElement("div");
    label.className = "meta";
    label.textContent = "Server copy of the source:";
    box.append(label, pre);
  }
  const actions = document.createElement("div");
  actions.className = "actions";
  if (serverCopy) {
    const reload = document.createElement("button");
    reload.type = "button";
    reload.className = "primary";
    reload.textContent = "Reload server copy";
    reload.addEventListener("click", () => {
      if (kind === "program") fillProgram(serverCopy); else fillCollection(serverCopy);
      notify(`Loaded revision ${serverCopy.revision} from the server.`, "info");
    });
    actions.append(reload);
  }
  const keep = document.createElement("button");
  keep.type = "button";
  keep.textContent = keepLabel;
  keep.addEventListener("click", () => { box.hidden = true; });
  actions.append(keep);
  box.append(actions);
  box.hidden = false;
}

async function handleConflict(kind, err) {
  // Fetch the newer server copy so the user can see it; never overwrite it.
  try {
    const fresh = kind === "program"
      ? await store.getProgram(state.program.id)
      : await store.getCollection(state.collection.id);
    showConflict(kind, err, fresh, "Keep my edits");
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      if (kind === "program") { state.program = null; $("program-meta").textContent = "deleted on server"; }
      showConflict(kind, err, null, "OK");
    } else {
      notify(`Conflict, and the server copy could not be loaded: ${explain(e)}`);
    }
  }
}

async function saveProgram() {
  const draft = readProgramForm();
  showFieldError("program", null, programInputs());
  try {
    const saved = state.program
      ? await store.updateProgram(state.program.id, state.program.revision, draft)
      : await store.createProgram(draft);
    fillProgram(saved);
    notify(`Saved “${saved.name}” (revision ${saved.revision}).`, "info");
    await loadPrograms();
  } catch (err) {
    if (err instanceof ApiError && err.isConflict) return handleConflict("program", err);
    if (err instanceof ApiError && err.status === 404 && state.program) {
      state.program = null;
      $("program-meta").textContent = "deleted on server — Save will create a new program";
      return showConflict("program", err, null, "OK");
    }
    showFieldError("program", err, programInputs());
  }
}

async function reloadProgram() {
  if (!state.program) return;
  if (programDirty() && !confirmDiscard("this program")) return;
  try {
    fillProgram(await store.getProgram(state.program.id));
    notify("Reloaded from the server.", "info");
  } catch (err) {
    notify(`Could not reload: ${explain(err)}`);
  }
}

async function deleteProgram() {
  if (!state.program || !confirm(`Delete program “${state.program.name}”? Test cases copied from it are not affected.`)) return;
  try {
    await store.deleteProgram(state.program.id, state.program.revision);
    state.programOpen = false;
    state.program = null;
    showPanel(null);
    notify("Program deleted.", "info");
    await loadPrograms();
  } catch (err) {
    if (err instanceof ApiError && err.isConflict) return handleConflict("program", err);
    notify(`Could not delete: ${explain(err)}`);
  }
}

async function runProgram() {
  const out = $("program-output");
  out.hidden = false;
  out.className = "output";
  out.textContent = "Running…";
  const outcome = await lambda.interpret($("program-source").value);
  if (outcome.status === "value") {
    out.className = "output ok";
    out.textContent = `${outcome.value} : ${outcome.type}`;
  } else {
    out.className = "output bad";
    out.textContent = `${describeOutcome(outcome)}\n${outcome.message ?? ""}`;
  }
  state.lastProgramOutcome = outcome;
}

async function caseFromProgram() {
  if (!state.collections.length) await loadCollections();
  if (!state.collections.length) return notify("Create a test collection first.");
  const select = $("pick-collection-select");
  select.innerHTML = "";
  for (const c of state.collections) select.append(new Option(c.name, c.id));
  if (state.collection) select.value = state.collection.id;
  const dialog = $("pick-collection");
  dialog.returnValue = "";
  dialog.showModal();
  dialog.addEventListener("close", async () => {
    if (dialog.returnValue !== "ok") return;
    const draft = readProgramForm();
    const outcome = state.lastProgramOutcome;
    const expected = outcome?.status === "value"
      ? { kind: "value", value: outcome.value }
      : outcome?.status === "syntax_error" ? { kind: "error", category: "syntax" }
      : outcome?.status === "type_error" ? { kind: "error", category: "type" }
      : { kind: "value", value: "" };
    if (state.collection?.id !== select.value) {
      if (!(await openCollection(select.value))) return;
    }
    openCaseForm(null, { name: draft.name, source: draft.source, expected, description: draft.description });
  }, { once: true });
}

// ------------------------------------------------------------ collection editor

const collectionInputs = () => ({ name: $("collection-name"), description: $("collection-description") });
const caseInputs = () => ({ name: $("case-name"), source: $("case-source"), description: $("case-description"), expected: $("case-value") });

function fillCollection(collection, { keepCaseForm = false } = {}) {
  state.collection = collection;
  state.collectionBase = collectionDraft(collection);
  $("collection-name").value = collection.name;
  $("collection-description").value = collection.description;
  $("collection-title").textContent = collection.name;
  $("collection-meta").textContent = `revision ${collection.revision} · saved ${fmtTime(collection.updated_at)}`;
  $("collection-conflict").hidden = true;
  showFieldError("collection", null, collectionInputs());
  if (!keepCaseForm) closeCaseForm();
  renderCases();
  updateDirtyBadges();
  renderLists();
}

async function openCollection(id) {
  if ((collectionDirty() || caseDirty()) && state.collection?.id !== id && !confirmDiscard("this collection")) return false;
  try {
    const collection = await store.getCollection(id);
    if (state.run?.collectionId !== id) state.run = null;
    fillCollection(collection);
    showPanel("collection");
    renderRun();
    return true;
  } catch (err) {
    notify(`Could not open collection: ${explain(err)}`);
    if (err instanceof ApiError && err.status === 404) loadCollections();
    return false;
  }
}

async function newCollection() {
  const name = prompt("Name for the new test collection:");
  if (name === null) return;
  try {
    const created = await store.createCollection({ name, description: "" });
    await loadCollections();
    await openCollection(created.id);
    notify(`Created collection “${created.name}”.`, "info");
  } catch (err) {
    notify(`Could not create collection: ${explain(err)}`);
  }
}

async function saveCollection() {
  showFieldError("collection", null, collectionInputs());
  try {
    const saved = await store.updateCollection(state.collection.id, state.collection.revision, readCollectionForm());
    fillCollection(saved, { keepCaseForm: true });
    notify("Collection details saved.", "info");
    await loadCollections();
  } catch (err) {
    if (err instanceof ApiError && err.isConflict) return handleConflict("collection", err);
    showFieldError("collection", err, collectionInputs());
  }
}

async function reloadCollection() {
  if ((collectionDirty() || caseDirty()) && !confirmDiscard("this collection")) return;
  try {
    fillCollection(await store.getCollection(state.collection.id));
    renderRun();
    notify("Collection reloaded from the server.", "info");
  } catch (err) {
    notify(`Could not reload: ${explain(err)}`);
  }
}

async function deleteCollection() {
  const c = state.collection;
  if (!c || !confirm(`Delete collection “${c.name}” and its ${c.cases.length} case(s)?`)) return;
  try {
    await store.deleteCollection(c.id, c.revision);
    state.collection = null;
    state.run = null;
    closeCaseForm();
    showPanel(null);
    notify("Collection deleted.", "info");
    await loadCollections();
  } catch (err) {
    if (err instanceof ApiError && err.isConflict) return handleConflict("collection", err);
    notify(`Could not delete: ${explain(err)}`);
  }
}

// ------------------------------------------------------------ cases

function renderCases() {
  const body = $("case-rows");
  body.innerHTML = "";
  const cases = state.collection?.cases ?? [];
  $("case-count").textContent = `(${cases.length})`;
  const lastById = new Map((state.run?.results ?? []).map((r) => [r.caseId, r]));
  cases.forEach((c, index) => {
    const tr = document.createElement("tr");
    tr.dataset.caseId = c.id;
    const cell = (text) => { const td = document.createElement("td"); td.textContent = text; return td; };
    tr.append(cell(String(index + 1)), cell(c.name), cell(describeExpected(c.expected)));
    const last = document.createElement("td");
    const result = lastById.get(c.id);
    if (result) {
      const badge = document.createElement("span");
      const stale = resultIsStale(result, state.collection);
      badge.className = `badge ${stale ? "stale" : result.pass ? "pass" : "fail"}`;
      badge.textContent = stale ? `edited since run` : result.pass ? "PASS" : "FAIL";
      last.append(badge);
    }
    tr.append(last);
    const actions = document.createElement("td");
    actions.className = "actions-cell";
    const edit = document.createElement("button");
    edit.type = "button"; edit.textContent = "Edit";
    edit.addEventListener("click", () => openCaseForm(c.id));
    const del = document.createElement("button");
    del.type = "button"; del.textContent = "Delete"; del.className = "danger";
    del.addEventListener("click", () => deleteCase(c));
    actions.append(edit, del);
    tr.append(actions);
    body.append(tr);
  });
  if (!cases.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 5; td.className = "meta"; td.textContent = "No test cases yet. Add one, or use “Add as test case…” from a program.";
    tr.append(td);
    body.append(tr);
  }
  $("run-collection").disabled = state.running || !cases.length || !state.lambdaUp;
  $("run-collection").title = state.lambdaUp ? "" : "LAMBDA3 service is not reachable";
}

function fillCaseForm(d) {
  $("case-name").value = d.name;
  $("case-source").value = d.source;
  $("case-description").value = d.description;
  document.querySelector(`input[name=case-kind][value=${d.kind}]`).checked = true;
  $("case-value").value = d.value;
  $("case-category").value = d.category;
}

function openCaseForm(caseId, prefill = null) {
  if (caseDirty() && !confirmDiscard("the open test case")) return;
  const existing = caseId ? state.collection.cases.find((c) => c.id === caseId) : null;
  state.caseEditing = caseId ?? null;
  state.caseBase = caseDraft(existing);
  fillCaseForm(prefill ? caseDraft(prefill) : state.caseBase);
  $("case-form-title").textContent = existing ? `Edit case “${existing.name}”` : "New test case";
  showFieldError("case", null, caseInputs());
  $("case-form").hidden = false;
  showPanel("collection");
  updateDirtyBadges();
  $("case-name").focus();
}

function closeCaseForm() {
  state.caseEditing = undefined;
  $("case-form").hidden = true;
  updateDirtyBadges();
}

async function saveCase(event) {
  event.preventDefault();
  const c = state.collection;
  const fields = caseFromDraft(readCaseForm());
  showFieldError("case", null, caseInputs());
  try {
    const saved = state.caseEditing
      ? await store.updateCase(c.id, state.caseEditing, c.revision, fields)
      : await store.addCase(c.id, c.revision, fields);
    closeCaseForm();
    fillCollection(saved);
    notify("Test case saved.", "info");
    loadCollections();
  } catch (err) {
    if (err instanceof ApiError && err.isConflict) return handleConflict("collection", err);
    showFieldError("case", err, caseInputs());
  }
}

async function deleteCase(testCase) {
  if (!confirm(`Delete test case “${testCase.name}”?`)) return;
  const c = state.collection;
  try {
    const saved = await store.deleteCase(c.id, testCase.id, c.revision);
    if (state.caseEditing === testCase.id) closeCaseForm();
    fillCollection(saved, { keepCaseForm: state.caseEditing !== undefined });
    notify("Test case deleted.", "info");
  } catch (err) {
    if (err instanceof ApiError && err.isConflict) return handleConflict("collection", err);
    notify(`Could not delete case: ${explain(err)}`);
  }
}

// ------------------------------------------------------------ running

function renderRun() {
  const box = $("run-summary");
  const run = state.run;
  if (!run || run.collectionId !== state.collection?.id) { box.hidden = true; return; }
  box.innerHTML = "";
  const done = run.results.length;
  const head = document.createElement("strong");
  head.textContent = state.running
    ? `Running… ${done} done: ${run.passed} passed, ${run.failed} failed`
    : `Run of revision ${run.revision}: ${run.passed} passed, ${run.failed} failed (of ${done})`;
  box.append(head);
  const list = document.createElement("ol");
  for (const r of run.results) {
    const li = document.createElement("li");
    const badge = document.createElement("span");
    badge.className = `badge ${r.pass ? "pass" : "fail"}`;
    badge.textContent = r.pass ? "PASS" : "FAIL";
    const stale = resultIsStale(r, state.collection);
    li.append(badge, ` ${r.name} — ${r.reason}`);
    if (stale) {
      const note = document.createElement("span");
      note.className = "badge stale";
      note.textContent = stale === "deleted" ? "case deleted since run" : "case edited since run";
      li.append(" ", note);
    }
    li.title = `case ${r.caseId}\n\n${r.source}`;
    list.append(li);
  }
  box.append(list);
  box.className = `run-summary ${state.running ? "" : run.failed ? "somefail" : "allpass"}`;
  box.hidden = false;
}

async function runCurrentCollection() {
  if (state.running || !state.collection) return;
  state.running = true;
  state.run = { collectionId: state.collection.id, revision: state.collection.revision, results: [], passed: 0, failed: 0 };
  renderCases();
  renderRun();
  try {
    state.run = await runCollection(state.collection, lambda, {
      onResult: (_result, partial) => { state.run = partial; renderRun(); renderCases(); },
    });
  } finally {
    state.running = false;
    renderRun();
    renderCases();
  }
}

// ------------------------------------------------------------ startup

async function checkServices() {
  try {
    await store.health();
    $("db-status").textContent = "database: connected";
    $("db-status").className = "pill ok";
  } catch {
    $("db-status").textContent = "database: unreachable";
    $("db-status").className = "pill bad";
  }
  state.lambdaUp = await lambda.health();
  $("lambda-status").textContent = state.lambdaUp ? "LAMBDA3: connected" : "LAMBDA3: unreachable";
  $("lambda-status").className = `pill ${state.lambdaUp ? "ok" : "bad"}`;
  $("run-program").disabled = !state.lambdaUp;
  renderCases();
}

$("new-program").addEventListener("click", newProgram);
$("save-program").addEventListener("click", saveProgram);
$("reload-program").addEventListener("click", reloadProgram);
$("delete-program").addEventListener("click", deleteProgram);
$("run-program").addEventListener("click", runProgram);
$("case-from-program").addEventListener("click", caseFromProgram);
$("new-collection").addEventListener("click", newCollection);
$("save-collection").addEventListener("click", saveCollection);
$("reload-collection").addEventListener("click", reloadCollection);
$("delete-collection").addEventListener("click", deleteCollection);
$("add-case").addEventListener("click", () => openCaseForm(null));
$("cancel-case").addEventListener("click", () => { if (!caseDirty() || confirmDiscard("this test case")) closeCaseForm(); });
$("case-form").addEventListener("submit", saveCase);
$("run-collection").addEventListener("click", runCurrentCollection);
$("more-programs").addEventListener("click", () => loadPrograms(true));
$("more-collections").addEventListener("click", () => loadCollections(true));
$("refresh-lists").addEventListener("click", () => { loadPrograms(); loadCollections(); checkServices(); });
document.addEventListener("input", updateDirtyBadges);
document.addEventListener("change", updateDirtyBadges);

window.studio = { state, store, lambda }; // for debugging and browser tests

showPanel(null);
checkServices();
loadPrograms();
loadCollections();
