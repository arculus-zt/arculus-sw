const fs = require('fs');
const path = require('path');
 
let cache = null;
 
function loadTelemetryJSON() {
  if (cache) return cache;
  const p = path.join(__dirname, '..', 'configs', 'drone_telemetry.json');
  cache = JSON.parse(fs.readFileSync(p, 'utf8'));
  return cache;
}
 
function getRandomTelemetry(attackType) {
  const data = loadTelemetryJSON();
  const arr = data[attackType];
  if (!arr || !arr.length) {
    throw new Error(`No telemetry sets for attackType="${attackType}"`);
  }
  const idx = Math.floor(Math.random() * arr.length);
  return arr[idx];
}
 
module.exports = { loadTelemetryJSON, getRandomTelemetry };