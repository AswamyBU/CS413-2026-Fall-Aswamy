// DOM wiring only: builds the board, forwards button clicks to the Player,
// and paints the Player's view. Search lives on the server; transport in
// rpc.js; event-to-view logic in board.js.

import { createRpcClient, RpcError, STREAM_NOT_FOUND } from "./rpc.js";
import { cellState, describeEvent } from "./board.js";
import { Player } from "./player.js";

const $ = (id) => document.getElementById(id);
const els = {
  board: $("board"), status: $("status"), error: $("error"), errorText: $("error-text"),
  start: $("start"), step: $("step"), play: $("play"), nextSolution: $("next-solution"),
  reset: $("reset"), restart: $("restart"), size: $("size"), speed: $("speed"),
  speedLabel: $("speed-label"), log: $("log"), solutions: $("solutions"),
  events: $("events"), tries: $("tries"), rejects: $("rejects"), backtracks: $("backtracks"),
  lastSolution: $("last-solution"),
};
const MAX_LOG = 200;
let cells = [];

function buildBoard(size) {
  els.board.innerHTML = "";
  els.board.style.setProperty("--n", size);
  cells = [];
  for (let r = 0; r < size; r++) {
    const row = [];
    for (let c = 0; c < size; c++) {
      const cell = document.createElement("div");
      cell.className = "cell " + ((r + c) % 2 ? "dark" : "light");
      cell.dataset.row = r;
      cell.dataset.col = c;
      els.board.appendChild(cell);
      row.push(cell);
    }
    cells.push(row);
  }
}

function paintBoard(view) {
  if (cells.length !== view.size) buildBoard(view.size);
  for (let r = 0; r < view.size; r++) {
    for (let c = 0; c < view.size; c++) {
      const { queen, state } = cellState(view, r, c);
      const cell = cells[r][c];
      const base = "cell " + ((r + c) % 2 ? "dark" : "light");
      cell.className = state ? `${base} ${state}` : base;
      cell.textContent = queen ? "♛" : state === "reject" ? "✕" : state === "try" ? "?" : "";
    }
  }
}

const STATUS_TEXT = {
  idle: "Press Start to open a search.",
  ready: "Ready: Step, Play, or Next solution.",
  playing: "Playing…",
  busy: "Working…",
  complete: "Search complete: every solution has been found.",
  error: "Stopped by an error.",
};

function render(p) {
  const v = p.view;
  paintBoard(v);
  els.solutions.textContent = v.solutions;
  els.events.textContent = v.events;
  els.tries.textContent = v.stats.try;
  els.rejects.textContent = v.stats.reject;
  els.backtracks.textContent = v.stats.backtrack;
  els.lastSolution.textContent = v.lastSolution ? `[${v.lastSolution.join(", ")}]` : "—";

  let status = STATUS_TEXT[p.state];
  if (p.state === "complete") status = `Search complete: ${v.solutions} solutions, no more remain.`;
  else if (v.lastEvent === "solution" && p.state !== "busy") status = `Solution #${v.solutions} found.`;
  els.status.textContent = status;
  els.status.dataset.state = v.lastEvent === "solution" && p.state !== "complete" ? "solution" : p.state;
  document.body.dataset.state = p.state;

  const live = p.started && p.state !== "complete" && p.state !== "busy";
  els.start.textContent = p.state === "idle" ? "Start" : "Restart";
  els.start.disabled = p.state === "busy";
  els.step.disabled = !live;
  els.nextSolution.disabled = !live;
  els.play.disabled = !live;
  els.play.textContent = p.state === "playing" ? "Pause" : "Play";
  els.reset.disabled = p.state === "busy" || p.state === "idle";
  els.size.disabled = p.state === "busy";
  els.restart.hidden = p.state !== "complete";
  if (p.state !== "error") els.error.hidden = true;
}

function log(ev) {
  const li = document.createElement("li");
  li.textContent = describeEvent(ev);
  li.className = `log-${ev.event}`;
  els.log.prepend(li);
  while (els.log.childElementCount > MAX_LOG) els.log.lastElementChild.remove();
}

function showError(err) {
  let text = err && err.message ? err.message : String(err);
  if (err instanceof RpcError && err.code === STREAM_NOT_FOUND) {
    text = "The search stream expired or was closed on the server. Press Restart.";
  } else if (err instanceof RpcError) {
    text = `RPC error ${err.code}: ${err.message}`;
  }
  els.errorText.textContent = text;
  els.error.hidden = false;
}

const player = new Player({
  rpc: createRpcClient({ url: "/rpc" }),
  size: Number(els.size.value),
  delay: Number(els.speed.value),
  onChange: render,
  onEvent: log,
  onError: showError,
});
window.queensPlayer = player; // handy for manual debugging and browser tests

function clearLog() { els.log.innerHTML = ""; }

els.start.addEventListener("click", () => { clearLog(); player.start(Number(els.size.value)); });
els.restart.addEventListener("click", () => { clearLog(); player.start(Number(els.size.value)); });
els.step.addEventListener("click", () => player.step());
els.play.addEventListener("click", () => player.toggle());
els.nextSolution.addEventListener("click", () => player.nextSolution());
els.reset.addEventListener("click", () => { clearLog(); player.reset(); });
els.size.addEventListener("change", () => {
  clearLog();
  player.size = Number(els.size.value);
  player.reset();
});
function updateSpeed() {
  player.setDelay(els.speed.value);
  els.speedLabel.textContent = `${els.speed.value} ms/event`;
}
els.speed.addEventListener("input", updateSpeed);
$("error-dismiss").addEventListener("click", () => { els.error.hidden = true; });

updateSpeed();
render(player);
