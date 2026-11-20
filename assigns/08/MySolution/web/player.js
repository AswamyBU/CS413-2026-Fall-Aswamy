// Playback controller: owns the stream id, a small event buffer, and the
// play/pause timer. It requests events only when the buffer is empty, so the
// client never holds more than one batch ahead of what has been shown.
// No DOM here: main.js passes callbacks; tests pass fakes.

import { applyEvent, initialView } from "./board.js";

export const PLAY_BATCH = 8;   // events per queens.next during normal playback
export const FAST_BATCH = 32;  // events per queens.next during "Next solution"

export class Player {
  constructor({
    rpc,
    size = 8,
    delay = 200,
    onChange = () => {},
    onEvent = () => {},
    onError = () => {},
    schedule = (fn, ms) => setTimeout(fn, ms),
    cancel = (handle) => clearTimeout(handle),
  }) {
    Object.assign(this, { rpc, size, delay, onChange, onEvent, onError, schedule, cancel });
    this.streamId = null;
    this.buffer = [];
    this.serverDone = false;
    this.view = initialView(size);
    this.state = "idle";      // idle | ready | playing | busy | complete | error
    this.error = null;
    this.timer = null;
    this.generation = 0;      // bumps on start/reset so stale async work stops
    this.requests = 0;        // queens.next calls made for the current stream
  }

  get started() { return this.streamId !== null && this.state !== "error"; }

  _set(state) {
    this.state = state;
    this.onChange(this);
  }

  _fail(err) {
    this._stopTimer();
    this.error = err;
    this._set("error");
    this.onError(err);
  }

  _stopTimer() {
    if (this.timer !== null) {
      this.cancel(this.timer);
      this.timer = null;
    }
  }

  async _closeQuietly() {
    const id = this.streamId;
    this.streamId = null;
    if (id) {
      try { await this.rpc.close(id); } catch { /* already gone or offline */ }
    }
  }

  async start(size = this.size) {
    const gen = ++this.generation;
    this._stopTimer();
    await this._closeQuietly();
    this.size = size;
    this.buffer = [];
    this.serverDone = false;
    this.requests = 0;
    this.error = null;
    this.view = initialView(size);
    this._set("busy");
    try {
      const result = await this.rpc.open(size);
      if (gen !== this.generation) return;
      this.streamId = result.stream_id;
      this._set("ready");
    } catch (err) {
      if (gen === this.generation) this._fail(err);
    }
  }

  async reset() {
    ++this.generation;
    this._stopTimer();
    await this._closeQuietly();
    this.buffer = [];
    this.serverDone = false;
    this.requests = 0;
    this.error = null;
    this.view = initialView(this.size);
    this._set("idle");
  }

  async _nextEvent(limit) {
    if (this.buffer.length === 0 && !this.serverDone) {
      const gen = this.generation;
      this.requests += 1;
      const result = await this.rpc.next(this.streamId, limit);
      if (gen !== this.generation) return null;
      this.buffer.push(...result.events);
      // When done, buffered events may still be unplayed; keep the id so
      // reset/restart can close the server's exhausted record.
      this.serverDone = result.done;
    }
    return this.buffer.length ? this.buffer.shift() : null;
  }

  // Apply one event. Returns the event, or null if nothing happened.
  async _advance(limit) {
    const gen = this.generation;
    const ev = await this._nextEvent(limit);
    if (ev === null || gen !== this.generation) return null;
    this.view = applyEvent(this.view, ev);
    this.onEvent(ev, this);
    if (ev.event === "done") {
      this._stopTimer();
      this._set("complete");
    } else {
      this.onChange(this);
    }
    return ev;
  }

  async step() {
    if (!this.started || this.state === "complete" || this.state === "busy") return null;
    this._stopTimer();
    if (this.state === "playing") this._set("ready");
    this.state = "busy";
    try {
      const ev = await this._advance(PLAY_BATCH);
      if (this.state === "busy") this._set("ready");
      return ev;
    } catch (err) {
      this._fail(err);
      return null;
    }
  }

  play() {
    if (!this.started || this.state !== "ready") return;
    this._set("playing");
    const gen = this.generation;
    const tick = async () => {
      this.timer = null;
      if (gen !== this.generation || this.state !== "playing") return;
      try {
        await this._advance(PLAY_BATCH);
      } catch (err) {
        this._fail(err);
        return;
      }
      if (gen === this.generation && this.state === "playing") {
        this.timer = this.schedule(tick, this.delay);
      }
    };
    this.timer = this.schedule(tick, 0);
  }

  pause() {
    this._stopTimer();
    if (this.state === "playing") this._set("ready");
  }

  toggle() {
    if (this.state === "playing") this.pause();
    else this.play();
  }

  setDelay(ms) {
    this.delay = Math.max(0, Number(ms) || 0);
  }

  // Run until the next solution (or done) without per-event delays.
  async nextSolution() {
    if (!this.started || this.state === "complete" || this.state === "busy") return null;
    this._stopTimer();
    const gen = this.generation;
    this.state = "busy";
    try {
      for (;;) {
        const ev = await this._advance(FAST_BATCH);
        if (gen !== this.generation) return null;
        if (ev === null || ev.event === "solution" || ev.event === "done") {
          if (this.state === "busy") this._set("ready");
          return ev;
        }
      }
    } catch (err) {
      this._fail(err);
      return null;
    }
  }
}
