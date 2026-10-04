// View: renders the model snapshot returned by the server and forwards
// user intents to the controller's HTTP endpoints.  It contains no language
// analysis and no state rules: which buttons are enabled, and why, comes
// from the snapshot.  All user/program text is inserted with textContent,
// so HTML-like source or output is shown literally.
"use strict";

const $ = (id) => document.getElementById(id);
const STATUS_TEXT = {
  ok: "Success",
  input_error: "Error (invalid input)",
  language_error: "Error (program)",
  backend_failure: "Failure (backend)",
  not_implemented: "Not implemented",
  unavailable: "Unavailable",
};

let state = null;        // last snapshot from the server
let pending = null;      // label of the request in flight, if any
let requestError = null; // last network-level failure, shown until next success
let localEdit = false;   // editor changed and not yet acknowledged
let editSeq = 0;         // bumps on every keystroke
let queue = Promise.resolve();

// ---- talking to the controller --------------------------------------------

// Requests are serialised so an Apply never overtakes the edit before it.
function send(label, method, url, body) {
  const run = async () => {
    // Controls are disabled while busy, which drops keyboard focus; remember
    // the focused control so it can be restored afterwards.
    const focused = document.activeElement;
    pending = label;
    render();
    try {
      const init = { method };
      if (body instanceof FormData) init.body = body;
      else if (body !== undefined) {
        init.headers = { "Content-Type": "application/json" };
        init.body = JSON.stringify(body);
      }
      const resp = await fetch(url, init);
      state = await resp.json();
      requestError = null;
    } catch (err) {
      // Network/server failure: keep the editor contents, re-sync state.
      requestError = `Request failed (${err.message}). Your source is preserved; try again.`;
      try { state = await (await fetch("/api/state")).json(); } catch (_) { /* offline */ }
    } finally {
      pending = null;
      render();
      if (focused && focused !== document.body && document.activeElement === document.body
          && document.contains(focused) && !focused.disabled) focused.focus();
    }
  };
  queue = queue.then(run, run);
  return queue;
}

function sendDraft() {
  const seq = editSeq;
  const text = $("editor").value;
  // Only stop treating the editor as authoritative once the server has seen
  // the latest keystroke; otherwise render() could overwrite newer typing.
  return send(null, "PUT", "/api/draft", { text }).then(() => {
    if (seq === editSeq) { localEdit = false; render(); }
  });
}

// ---- rendering -------------------------------------------------------------

function showStatus(text) { $("status").textContent = text; }

function render() {
  if (!state) return;
  const busy = Boolean(pending) || Boolean(state.busy);
  const dirty = state.dirty || localEdit;

  if (pending) showStatus(`Busy: ${pending}…`);
  else if (state.busy) showStatus(`Busy: running ${state.busy}…`);
  else showStatus(requestError ? `Ready. ${requestError}` : "Ready.");

  $("source-info").textContent = state.source
    ? `Applied source: ${state.source.name} — revision ${state.source.revision}`
    : "No source applied.";

  const editor = $("editor");
  if (!localEdit && editor.value !== state.draft.text) editor.value = state.draft.text;
  editor.readOnly = busy;
  editor.setAttribute("aria-busy", String(busy));

  $("dirty-info").textContent = dirty
    ? `Unapplied edits (editing: ${state.draft.name}).`
    : "No unapplied edits.";
  $("apply-button").disabled = busy || !dirty;
  $("discard-button").disabled = busy || !dirty;
  $("source-menu").disabled = busy || dirty;
  $("load-button").disabled = busy || dirty;

  const notice = $("notice");
  notice.textContent = state.notice ? state.notice.text : "";
  notice.className = state.notice ? `notice ${state.notice.level}` : "";
  if (state.notice && state.notice.level === "error") notice.textContent = "Error: " + state.notice.text;

  renderActions(busy, dirty);
  renderResults();
}

// Action buttons are created once (in server order) and updated in place,
// so keyboard focus stays on the button the user activated.
function renderActions(busy, dirty) {
  const box = $("actions");
  const reasons = $("action-reasons");
  reasons.replaceChildren();
  for (const a of state.actions) {
    let btn = box.querySelector(`[data-action="${a.id}"]`);
    if (!btn) {
      btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.action = a.id;
      btn.addEventListener("click", () =>
        send(`running ${btn.textContent}`, "POST", `/api/action/${a.id}`));
      box.append(btn);
    }
    btn.textContent = a.label;
    let reason = a.reason;
    if (!reason && busy) reason = "Busy.";
    if (!reason && dirty) reason = "Apply or discard your edits first.";
    btn.disabled = Boolean(reason);
    const id = `reason-${a.id}`;
    if (reason) {
      btn.setAttribute("aria-describedby", id);
      const li = document.createElement("li");
      li.id = id;
      li.textContent = `${a.label} disabled: ${reason}`;
      reasons.append(li);
    } else {
      btn.removeAttribute("aria-describedby");
    }
  }
}

function renderResults() {
  const list = $("results");
  list.replaceChildren();
  if (state.results.length === 0) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "No results for the current revision.";
    list.append(li);
    return;
  }
  for (const r of state.results.slice().reverse()) {  // newest first
    const li = document.createElement("li");
    li.className = `result ${r.status}`;
    const head = document.createElement("p");
    head.className = "result-head";
    head.textContent = `${r.operation} · revision ${r.revision} · ` +
      `${STATUS_TEXT[r.status] || r.status}: ${r.summary}`;
    li.append(head);
    if (r.output) {
      const pre = document.createElement("pre");
      pre.textContent = r.output;
      li.append(pre);
    }
    list.append(li);
  }
}

// ---- forwarding user intents -----------------------------------------------

$("editor").addEventListener("input", () => {
  localEdit = true;
  editSeq += 1;
  render();          // disables actions immediately
  sendDraft();
});

$("apply-button").addEventListener("click", () => send("applying edits", "POST", "/api/draft/apply"));
$("discard-button").addEventListener("click", () => {
  editSeq += 1;
  localEdit = false;
  send("discarding edits", "POST", "/api/draft/discard");
});

$("load-button").addEventListener("click", () => {
  const choice = $("source-menu").value;
  if (choice === "file") $("file-input").click();
  else if (choice === "manual") send("opening manual input", "POST", "/api/source/manual")
    .then(() => $("editor").focus());
  else send("loading example", "POST", `/api/source/example/${choice}`);
});

$("file-input").addEventListener("change", () => {
  const file = $("file-input").files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  $("file-input").value = "";
  send("uploading file", "POST", "/api/source/upload", form);
});

send("loading", "GET", "/api/state");
