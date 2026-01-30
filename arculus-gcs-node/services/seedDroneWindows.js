const pool = require('../modules/arculusDbConnection');

function makeWindow10(base, deltas) {
  return deltas.map(d => +(base + d).toFixed(3));
}

async function seedExampleWindowsForAllDrones() {
  const [devices] = await pool.promise().query(`SELECT device_id FROM trusted_device`);
  if (!devices.length) throw new Error('No rows in trusted_device.');

  const insertSql = `
    INSERT INTO drone_feature_windows
      (device_id, window_size, transmission_rate, energy_consumption, unauthorized_access, signal_strength, resource_usage)
    VALUES (?, 10, ?, ?, ?, ?, ?)
  `;

  for (const d of devices) {
    const deviceId = d.device_id;

    const transmission = makeWindow10(30 + deviceId * 0.01, [ -0.2, 0.4, 1.1, 0.2, -0.1, 0.6, 0.0, -0.3, 0.8, 3.5 ]);
    const energy       = makeWindow10(40 + deviceId * 0.02, [ -0.8, 0.1, 1.0, -0.2, 0.3, 0.5, 1.2, -0.4, 0.0, 6.8 ]);
    const unauth       = [0, 0, (deviceId % 3 === 0 ? 2 : 1), 0, 0, (deviceId % 2 === 0 ? 2 : 0), 1, 0, 0, (deviceId % 5 === 0 ? 3 : 1)];
    const signal       = makeWindow10(-70 - deviceId * 0.01, [ -1.0, -0.4, 0.3, -0.8, -0.1, 0.1, -0.3, 0.2, -0.2, -7.5 ]);

    const resourceUsage = 0.42;

    await pool.promise().query(insertSql, [
      deviceId,
      JSON.stringify(transmission),
      JSON.stringify(energy),
      JSON.stringify(unauth),
      JSON.stringify(signal),
      resourceUsage,
    ]);
  }

  return { inserted_for_devices: devices.length };
}

module.exports = { seedExampleWindowsForAllDrones };
