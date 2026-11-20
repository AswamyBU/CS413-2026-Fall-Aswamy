// Rendering model: a pure reducer from search events to a board view.
// No network, no DOM. main.js turns a view into cells; tests call it directly.

export function initialView(size) {
  return {
    size,
    board: [],          // queen column for rows 0..board.length-1
    cursor: null,       // { row, column, kind } of the latest event, if any
    conflicts: [],      // rows of queens that attack a rejected candidate
    solutions: 0,
    events: 0,
    stats: { try: 0, place: 0, reject: 0, backtrack: 0 },
    lastEvent: null,
    lastSolution: null,
    done: false,
  };
}

// Rows of queens on `board` that attack a candidate at (row, column).
export function attackers(board, row, column) {
  const rows = [];
  board.forEach((c, r) => {
    const distance = row - r;
    if (c === column || c === column - distance || c === column + distance) rows.push(r);
  });
  return rows;
}

export function applyEvent(view, ev) {
  const next = {
    ...view,
    events: view.events + 1,
    stats: { ...view.stats },
    lastEvent: ev.event,
    conflicts: [],
  };
  switch (ev.event) {
    case "try":
    case "place":
    case "backtrack":
      next.board = ev.board.slice();
      next.cursor = { row: ev.row, column: ev.column, kind: ev.event };
      next.stats[ev.event] += 1;
      break;
    case "reject":
      next.board = ev.board.slice();
      next.cursor = { row: ev.row, column: ev.column, kind: "reject" };
      next.conflicts = attackers(ev.board, ev.row, ev.column);
      next.stats.reject += 1;
      break;
    case "solution":
      next.board = ev.board.slice();
      next.cursor = null;
      next.solutions = typeof ev.number === "number" ? ev.number : view.solutions + 1;
      next.lastSolution = ev.board.slice();
      break;
    case "done":
      next.cursor = null;
      next.board = [];
      next.done = true;
      break;
    default:
      throw new Error(`unknown event ${ev.event}`);
  }
  return next;
}

// What one cell shows. Returns { queen: bool, state: "" | "try" | "place" |
// "reject" | "backtrack" | "conflict" | "solution" }.
export function cellState(view, row, column) {
  const queen = view.board[row] === column;
  const c = view.cursor;
  if (view.lastEvent === "solution" && queen) return { queen: true, state: "solution" };
  if (c && c.row === row && c.column === column) {
    // try/reject show a candidate; backtrack shows the queen just removed.
    return { queen: c.kind === "place" || queen, state: c.kind };
  }
  if (queen && view.conflicts.includes(row)) return { queen: true, state: "conflict" };
  return { queen, state: "" };
}

export function describeEvent(ev) {
  const at = (e) => `row ${e.row}, col ${e.column}`;
  switch (ev.event) {
    case "try": return `try ${at(ev)}`;
    case "place": return `place ${at(ev)} → [${ev.board.join(", ")}]`;
    case "reject": return `reject ${at(ev)} (attacked)`;
    case "backtrack": return `backtrack: remove ${at(ev)}`;
    case "solution": return `SOLUTION #${ev.number ?? "?"}: [${ev.board.join(", ")}]`;
    case "done": return "search complete: no more solutions";
    default: return JSON.stringify(ev);
  }
}
