// Independent TensorFlow.js 3.7.0 oracle for the shipped model graph.
const fs = require("fs");
const path = require("path");

const upstream = path.resolve(process.argv[2]);
const output = path.resolve(process.argv[3]);
const tf = require(path.resolve("tmp/p03-tfjs/node_modules/@tensorflow/tfjs"));

function loadWeights(model) {
  const base = path.join(upstream, "demo", "models", model);
  const manifest = JSON.parse(fs.readFileSync(path.join(base, "model.json"), "utf8"));
  const specs = manifest.weightsManifest.flatMap((group) => group.weights);
  const bytes = fs.readFileSync(path.join(base, "group1-shard1of1.bin"));
  const values = new Float32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 4);
  let offset = 0;
  return specs.map((spec) => {
    const count = spec.shape.reduce((a, b) => a * b, 1);
    const tensor = tf.tensor(values.slice(offset, offset + count), spec.shape, "float32");
    offset += count;
    return tensor;
  });
}

function writeF32(name, tensor) {
  const values = tensor.dataSync();
  const buffer = Buffer.alloc(values.length * 4);
  for (let i = 0; i < values.length; i += 1) buffer.writeFloatLE(values[i], i * 4);
  fs.writeFileSync(path.join(output, name), buffer);
}

fs.mkdirSync(output, { recursive: true });
const [k0, b0, k1, b1, k2, b2] = loadWeights("model1");
const size = 32 * 32 * 6;
const initial = Float32Array.from({ length: size }, (_, i) => Math.fround(Math.sin(i * 0.017) * 0.1));
const grid = tf.tensor(initial, [1, 32, 32, 6], "float32");
const first = tf.relu(tf.add(tf.conv2d(grid, k0, [1, 1], "same"), b0));
const hidden = tf.relu(tf.add(tf.conv2d(first, k1, [1, 1], "valid"), b1));
const delta = tf.add(tf.conv2d(hidden, k2, [1, 1], "valid"), b2);
const maskData = Float32Array.from({ length: 32 * 32 }, (_, i) => (i % 3 === 0 ? 0 : 1));
const mask = tf.tensor(maskData, [1, 32, 32, 1], "float32");
const cut = new Float32Array(size).fill(1);
const pos = new Float32Array(size);
const inputs = [[11,26],[25,20],[5,20],[19,6],[19,26],[5,12],[25,12],[11,6]];
const outputs = [[13,16],[17,16]];
for (let r = 0; r < 32; r += 1) for (let c = 0; c < 32; c += 1) {
  cut[(r * 32 + c) * 6 + 2] = 0;
  cut[(r * 32 + c) * 6 + 3] = 0;
}
for (const [r, c] of inputs) {
  for (let ch = 0; ch < 6; ch += 1) cut[(r * 32 + c) * 6 + ch] = 0;
  for (const ch of [1, 2, 4, 5]) pos[(r * 32 + c) * 6 + ch] = 1;
}
for (const [r, c] of outputs) {
  pos[(r * 32 + c) * 6 + 3] = 1;
  pos[(r * 32 + c) * 6 + 4] = 1;
  pos[(r * 32 + c) * 6 + 5] = 1;
}
let step = tf.add(
  tf.mul(tf.add(grid, tf.mul(delta, mask)), tf.tensor(cut, [1,32,32,6])),
  tf.tensor(pos, [1,32,32,6]),
);
const stepValues = step.dataSync().slice();
const observations = [0.02,0.02,-0.005,-0.005,0.12,0.12,-0.006,-0.006];
inputs.forEach(([r, c], i) => { stepValues[(r * 32 + c) * 6] += observations[i]; });
step = tf.tensor(stepValues, [1,32,32,6], "float32");
writeF32("local_delta.bin", delta);
writeF32("complete_step.bin", step);
console.log(JSON.stringify({tfjs: tf.version.tfjs, tensors: tf.memory().numTensors}));

