// AudioWorklet: play back converted PCM frames received from the main thread.
// A small ring/jitter buffer smooths network arrival jitter; underflow outputs
// silence rather than clicking.
class PlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._queue = [];      // array of Float32Array chunks
    this._current = null;
    this._offset = 0;
    this.port.onmessage = (e) => {
      if (e.data === "flush") {
        this._queue = [];
        this._current = null;
        this._offset = 0;
      } else {
        this._queue.push(e.data);
      }
    };
  }

  process(_inputs, outputs) {
    const out = outputs[0][0];
    if (!out) return true;
    for (let i = 0; i < out.length; i++) {
      if (!this._current || this._offset >= this._current.length) {
        this._current = this._queue.shift() || null;
        this._offset = 0;
      }
      out[i] = this._current ? this._current[this._offset++] : 0;
    }
    return true;
  }
}

registerProcessor("playback-processor", PlaybackProcessor);
