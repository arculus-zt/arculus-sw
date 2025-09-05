const path = require('path');
const fs = require('fs');
const pool = require('../modules/arculusDbConnection');// your mysql2 pool
const { getRandomTelemetry } = require('../lib/telemetry');
const { computeBayesianRisk, computeZeroTrustMetric, computeZTGrade, formatRemarks } = require('../lib/risk');

// Auth type constants
const NOAUTH = 'NOAUTH';
const AUTH_TOKEN_BASED = 'AUTH_TOKEN_BASED';
const AUTH_CERT_BASED = 'AUTH_CERT_BASED';

// Function to determine auth_type based on zt_grade
function getAuthType(zt_grade) {
  switch (zt_grade.toUpperCase()) {
    case 'A':
      return AUTH_CERT_BASED;
    case 'B':
    case 'C':
      return AUTH_TOKEN_BASED;
    case 'D':
    case 'E':
      return NOAUTH;
    default:
      // Fallback for unknown grades
      return NOAUTH;
  }
}
 
// helper: find device_id by drone name (supports underscore/space normalization like your SQL)
async function getDeviceId(conn, droneName) {
  const [rows] = await conn.query(
    `SELECT device_id, device_name
     FROM trusted_device
     WHERE REPLACE(device_name, '_', ' ') = ?`,
    [droneName]
  );
  if (!rows.length) throw new Error(`trusted_device not found: ${droneName}`);
  return rows[0].device_id;
}
 
// main: apply snapshot using telemetry from JSON
async function applySnapshotFromJson(attackMap /* object: droneName->attackType */) {
  const conn = await pool.promise().getConnection();
  try {
    await conn.beginTransaction();
 
    // (Optional) clean previous rows for the same set of drones
    const drones = Object.keys(attackMap);
    if (drones.length) {
      // delete risk rows
      await conn.query(
        `DELETE dsr FROM drone_security_risk dsr
         JOIN trusted_device td ON td.device_id = dsr.device_id
         WHERE REPLACE(td.device_name, '_', ' ') IN (${drones.map(() => '?').join(',')})`,
        drones
      );
      // delete telemetry rows
      await conn.query(
        `DELETE ddd FROM drone_device_data ddd
         JOIN trusted_device td ON td.device_id = ddd.device_id
         WHERE REPLACE(td.device_name, '_', ' ') IN (${drones.map(() => '?').join(',')})`,
        drones
      );
    }
 
    for (const droneName of drones) {
      const attackType = attackMap[droneName]; // 'Faker' | 'Flooder' | 'Physical Capture'
      var t = { transmission_rate: 8, energy_consumption: 20, unauthorized_access_attempts: 0, signal_strength: 90 };
      
      if (['Faker', 'Flooder', 'Physical Capture'].includes(attackType)) {
        t = getRandomTelemetry(attackType);
      } // else 'Normal' or unknown => use default t
 
      const deviceId = await getDeviceId(conn, droneName);
 
      const resource_usage = Math.round(((t.transmission_rate * t.energy_consumption) / 10) * 100) / 100;
 
      // Insert telemetry row
      await conn.query(
        `INSERT INTO drone_device_data
          (device_id, drone_name, transmission_rate, energy_consumption,
           unauthorized_access_attempts, signal_strength, gps_location, resource_usage)
         VALUES (?,?,?,?,?,?,NULL,?)`,
        [
          deviceId,
          droneName,
          t.transmission_rate,
          t.energy_consumption,
          t.unauthorized_access_attempts,
          t.signal_strength,
          resource_usage,
        ]
      );
 
      // Compute risk & ZT metrics in Node (replacing SQL math)
      const bayesian_risk = computeBayesianRisk(t);
      const zero_trust_metric = computeZeroTrustMetric(bayesian_risk);
      const zt_grade = computeZTGrade(zero_trust_metric);
      const auth_type = getAuthType(zt_grade); // NEW: Determine auth_type based on zt_grade
      const remarks = formatRemarks(t);
 
      // Insert risk row with auth_type
      await conn.query(
        `INSERT INTO drone_security_risk
          (device_id, drone_name, bayesian_risk, attack_type, zero_trust_metric, zt_grade, auth_type, remarks)
         VALUES (?,?,?,?,?,?,?,?)`,
        [deviceId, droneName, bayesian_risk, attackType, zero_trust_metric, zt_grade, auth_type, remarks]
      );
    }
 
    await conn.commit();
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}
 
module.exports = { applySnapshotFromJson, getAuthType, NOAUTH, AUTH_TOKEN_BASED, AUTH_CERT_BASED };