// services/ztGradeService.js
// Uses existing mysql2 pool from your software:
const pool = require('../modules/arculusDbConnection');

/**
 * ----------------------------
 * Math utilities
 * ----------------------------
 */
function sigmoid(x) {
  return 1 / (1 + Math.exp(-x));
}

function mean(arr) {
  const n = arr.length;
  if (!n) return 0;
  return arr.reduce((a, b) => a + b, 0) / n;
}

function std(arr) {
  const m = mean(arr);
  const n = arr.length;
  if (n <= 1) return 0;
  const v = arr.reduce((acc, x) => acc + (x - m) * (x - m), 0) / n;
  return Math.sqrt(v);
}

/**
 * anomaly_score_from_window: matches your Python behavior:
 * prob = sigmoid(abs(z_last) - z_th)
 */
function anomalyScoreFromWindow(arr, zTh = 2.0) {
  const m = mean(arr);
  const s = std(arr) + 1e-6;
  const z = (arr[arr.length - 1] - m) / s;
  return sigmoid(Math.abs(z) - zTh);
}

function discretizeAnomaly(prob, th = 0.5) {
  return prob > th ? 1 : 0;
}

/**
 * ----------------------------
 * Bayesian model CPDs (same as your Python CPDs)
 * We compute P(Trust=High | evidence on roots) by enumeration.
 * ----------------------------
 */

// Anomaly CPD: P(Anom=1 | Parent)
// Parent=0 -> 0.1 ; Parent=1 -> 0.9
function pAnomalyIs1(parentVal) {
  return parentVal === 1 ? 0.9 : 0.1;
}

// Flooder CPD: P(Flooder=1 | TrafficAnomaly)
function pFlooderIs1(trafficAnom) {
  return trafficAnom === 1 ? 0.8 : 0.05;
}

// PhysicalCapture CPD: P(PhysicalCapture=1 | SignalAnomaly)
function pPhysicalIs1(signalAnom) {
  return signalAnom === 1 ? 0.75 : 0.03;
}

// Faker CPD: evidence order (EnergyAnomaly, AccessAnomaly)
// columns: (EA=0,AA=0), (EA=0,AA=1), (EA=1,AA=0), (EA=1,AA=1)
// P(Faker=1 | EA,AA): [0.02, 0.4, 0.4, 0.9]
function pFakerIs1(energyAnom, accessAnom) {
  const idx = energyAnom * 2 + accessAnom; // (0,0)->0 (0,1)->1 (1,0)->2 (1,1)->3
  const table = [0.02, 0.4, 0.4, 0.9];
  return table[idx];
}

// Trust CPD: evidence order (Flooder, Faker, PhysicalCapture)
// columns: (0,0,0),(0,0,1),(0,1,0),(0,1,1),(1,0,0),(1,0,1),(1,1,0),(1,1,1)
// P(Trust=High | F,Fk,P): [0.01,0.05,0.07,0.15,0.10,0.18,0.22,0.35]
function pTrustHigh(flooder, faker, physical) {
  const idx = flooder * 4 + faker * 2 + physical;
  const table = [0.01, 0.05, 0.07, 0.15, 0.10, 0.18, 0.22, 0.35];
  return table[idx];
}

/**
 * Compute P(Trust=High) given evidence on roots:
 * evidence = { TransmissionRate, EnergyConsumption, UnauthorizedAccess, SignalStrength }
 * These are 0/1.
 */
function computeTrustFromEvidence(evidence) {
  const TR = evidence.TransmissionRate;
  const EC = evidence.EnergyConsumption;
  const UA = evidence.UnauthorizedAccess;
  const SS = evidence.SignalStrength;

  let trustHighSum = 0;
  let total = 0;

  // enumerate anomaly nodes
  for (const TA of [0, 1]) {
    const pTA = TA === 1 ? pAnomalyIs1(TR) : (1 - pAnomalyIs1(TR));

    for (const EA of [0, 1]) {
      const pEA = EA === 1 ? pAnomalyIs1(EC) : (1 - pAnomalyIs1(EC));

      for (const AA of [0, 1]) {
        const pAA = AA === 1 ? pAnomalyIs1(UA) : (1 - pAnomalyIs1(UA));

        for (const SA of [0, 1]) {
          const pSA = SA === 1 ? pAnomalyIs1(SS) : (1 - pAnomalyIs1(SS));

          // enumerate attack nodes
          for (const F of [0, 1]) {
            const pF = F === 1 ? pFlooderIs1(TA) : (1 - pFlooderIs1(TA));

            for (const FK of [0, 1]) {
              const pFK = FK === 1 ? pFakerIs1(EA, AA) : (1 - pFakerIs1(EA, AA));

              for (const P of [0, 1]) {
                const pP = P === 1 ? pPhysicalIs1(SA) : (1 - pPhysicalIs1(SA));

                const joint = pTA * pEA * pAA * pSA * pF * pFK * pP;
                const tHigh = pTrustHigh(F, FK, P);

                trustHighSum += joint * tHigh;
                total += joint;
              }
            }
          }
        }
      }
    }
  }

  return total > 0 ? (trustHighSum / total) : 0;
}

/**
 * ----------------------------
 * ZT metric + grade (same structure as earlier)
 * ----------------------------
 */
function computeEaser(resourceUsage, threshold = 1.0) {
  return resourceUsage >= threshold ? 1.0 : sigmoid(resourceUsage);
}

function computeZtMetric(trustScore, resourceUsage, maxScore = 150.0) {
  const baseRisk = 1.0 - trustScore;
  const easer = computeEaser(resourceUsage);
  return baseRisk * easer * maxScore;
}

function gradeFromZt(z) {
  if (z >= 80) return 'A';
  if (z >= 50) return 'B';
  if (z >= 30) return 'C';
  if (z >= 15) return 'D';
  return 'E';
}

/**
 * Parse MySQL JSON values safely (mysql2 may return as string or object depending on config)
 */
function parseJsonArray(val) {
  if (val == null) return [];
  if (Array.isArray(val)) return val;
  if (Buffer.isBuffer(val)) return JSON.parse(val.toString('utf8'));
  if (typeof val === 'string') return JSON.parse(val);
  return val; // fallback
}

/**
 * ----------------------------------------
 * MAIN API: computeAndStoreZtGrade(deviceName)
 * ----------------------------------------
 * - Finds latest window row for device_name
 * - Computes trust -> zt_metric -> grade
 * - Updates that window row with results
 * - Returns results
 */
async function computeAndStoreZtGrade(deviceName, opts = {}) {
  const {
    zTh = 2.0,
    anomalyTh = 0.5,
    unauthorizedMode = 'any_positive', // 'any_positive' | 'mean_gt_0_5'
    defaultResourceUsage = 0.5,
  } = opts;

  // 1) fetch latest window for that device_name
  const fetchSql = `
    SELECT td.device_id, td.device_name,
           w.window_id, w.window_size,
           w.transmission_rate, w.energy_consumption, w.unauthorized_access, w.signal_strength,
           w.resource_usage
    FROM trusted_device td
    JOIN drone_feature_windows w ON w.device_id = td.device_id
    WHERE td.device_name = ?
    ORDER BY w.collected_at DESC
    LIMIT 1
  `;

  const [rows] = await pool.promise().query(fetchSql, [deviceName]);
  if (!rows || rows.length === 0) {
    throw new Error(`No feature window found for device_name='${deviceName}'. Insert data into drone_feature_windows first.`);
  }

  const row = rows[0];

  const tr = parseJsonArray(row.transmission_rate).map(Number);
  const ec = parseJsonArray(row.energy_consumption).map(Number);
  const ua = parseJsonArray(row.unauthorized_access).map(Number);
  const ss = parseJsonArray(row.signal_strength).map(Number);

  // 2) compute evidence from windows (same intent as your Python)
  const trProb = anomalyScoreFromWindow(tr, zTh);
  const ecProb = anomalyScoreFromWindow(ec, zTh);
  const ssProb = anomalyScoreFromWindow(ss, zTh);

  const trEv = discretizeAnomaly(trProb, anomalyTh);
  const ecEv = discretizeAnomaly(ecProb, anomalyTh);
  const ssEv = discretizeAnomaly(ssProb, anomalyTh);

  let uaEv;
  if (unauthorizedMode === 'mean_gt_0_5') {
    uaEv = mean(ua) > 0.5 ? 1 : 0;
  } else {
    // recommended for count-like data
    uaEv = ua.some(x => x > 0) ? 1 : 0;
  }

  const evidence = {
    TransmissionRate: trEv,
    EnergyConsumption: ecEv,
    UnauthorizedAccess: uaEv,
    SignalStrength: ssEv,
  };

  // 3) Bayesian inference (enumeration)
  const trustScore = computeTrustFromEvidence(evidence);

  // 4) ZT metric + grade
  const resourceUsage = row.resource_usage != null ? Number(row.resource_usage) : defaultResourceUsage;
  const ztMetric = computeZtMetric(trustScore, resourceUsage);
  const ztGrade = gradeFromZt(ztMetric);

  // 5) update the same window row
  const updateSql = `
    UPDATE drone_feature_windows
    SET trust_score = ?, zt_metric = ?, zt_grade = ?
    WHERE window_id = ?
  `;
  await pool.promise().query(updateSql, [trustScore, ztMetric, ztGrade, row.window_id]);

  // 6) return result for your software stack
  return {
    device_id: row.device_id,
    device_name: row.device_name,
    window_id: row.window_id,
    evidence,
    trust_score: trustScore,
    resource_usage: resourceUsage,
    zt_metric: ztMetric,
    zt_grade: ztGrade,
  };
}

module.exports = {
  computeAndStoreZtGrade,
};
