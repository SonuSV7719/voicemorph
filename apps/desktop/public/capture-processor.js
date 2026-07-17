// AudioWorklet: capture mic PCM and post fixed-size mono float32 frames to the
// main thread. Runs on the audio render thread for low, stable latency.
class CaptureProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const frame = (options && options.processorOptions && options.processorOptions.frameSize) || 4800;
    this._frameSize = frame;
    this._buf = new Float32Array(this._frameSize);
    this._pos = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;
    const channel = input[0]; // mono
    if (!channel) return true;
    for (let i = 0; i < channel.length; i++) {
      this._buf[this._pos++] = channel[i];
      if (this._pos >= this._frameSize) {
        // Transfer a copy so the buffer can be reused immediately.
        this.port.postMessage(this._buf.slice(0), []);
        this._pos = 0;
      }
    }
    return true;
  }
}

registerProcessor("capture-processor", CaptureProcessor);
