function round2(n) { return Math.round(n * 100) / 100; }
function clamp01_100(n) { return Math.max(0, Math.min(100, n)); }


function computeBayesianRisk({ transmission_rate: tr, energy_consumption: en, unauthorized_access_attempts: ua, signal_strength: rssi }) {
  // --- Helpers ----------------------------------------------------
  const round2 = (x) => Math.round(x * 100) / 100;
  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
 
  // Discretize like the Python code's thresholds (strict > threshold -> 1, else 0)
  // Python thresholds: TransmissionRate: 0.6, UnauthorizedAccess: 0.5, others default 0.5
  function discretizeInputs({ tr, en, ua, rssi }) {
    const thresholds = {
      TransmissionRate: 0.6,
      UnauthorizedAccess: 0.5,
      EnergyConsumption: 0.5,
      SignalStrength: 0.5,
    };
    return {
      TransmissionRate: tr > thresholds.TransmissionRate ? 1 : 0,
      EnergyConsumption: en > thresholds.EnergyConsumption ? 1 : 0,
      UnauthorizedAccess: ua > thresholds.UnauthorizedAccess ? 1 : 0,
      SignalStrength: rssi > thresholds.SignalStrength ? 1 : 0,
    };
  }
 
  // Attack probability given binary evidence (mirrors generate_weighted_cpd in spirit)
  // score = sum_i weights[i] * evidence[i], clipped to [bias, 0.95]
  function attackProb(evidenceArray, weights, bias = 0.01) {
    const score = evidenceArray.reduce((s, v, i) => s + weights[i] * v, 0);
    return clamp(score, bias, 0.95);
  }
 
  // Expected Trust=High by marginalizing attacker Bernoullis against the CPD
  function expectedTrustHigh(pF, pK, pP) {
    // Order of evidence in the Python CPD: [Flooder, Faker, PhysicalCapture]
    // Columns correspond to binary combos (0/1) in lexicographic order:
    // 000, 001, 010, 011, 100, 101, 110, 111
    const trustHigh = [0.01, 0.04, 0.07, 0.10, 0.08, 0.12, 0.15, 0.25];
 
    const probsAttackers = [
      (1 - pF) * (1 - pK) * (1 - pP), // 000
      (1 - pF) * (1 - pK) * pP,       // 001
      (1 - pF) * pK * (1 - pP),       // 010
      (1 - pF) * pK * pP,             // 011
      pF * (1 - pK) * (1 - pP),       // 100
      pF * (1 - pK) * pP,             // 101
      pF * pK * (1 - pP),             // 110
      pF * pK * pP,                   // 111
    ];
 
    return trustHigh.reduce((sum, pTrust, i) => sum + pTrust * probsAttackers[i], 0);
  }
 
  // --- Model (ported from Python) ---------------------------------
  // 1) Discretize inputs
  const disc = discretizeInputs({ tr, en, ua, rssi });
  const ev = [
    disc.TransmissionRate,
    disc.EnergyConsumption,
    disc.UnauthorizedAccess,
    disc.SignalStrength,
  ];
 
  // 2) Attacker nodes as weighted influences of the 4 inputs
  //    (same weights used in Python)
  const pFlooder = attackProb(ev, [0.6, 0.1, 0.1, 0.2]); // Flooder mostly by TransmissionRate
  const pFaker   = attackProb(ev, [0.1, 0.6, 0.1, 0.2]); // Faker mostly by EnergyConsumption
  const pPhys    = attackProb(ev, [0.2, 0.1, 0.1, 0.6]); // PhysicalCapture mostly by SignalStrength
 
  // 3) Trust CPD expectation → P(Trust=High)
  const pTrustHigh = expectedTrustHigh(pFlooder, pFaker, pPhys);
 
  // 4) Risk = (1 - P(Trust=High)) * 100 (like Python's base_risk * 100)
  const risk = clamp((1 - pTrustHigh) * 100, 0, 100);
 
  return round2(risk);
}
 
function computeZeroTrustMetric(bayesian_risk) {
  //return clamp01_100(round2(100 - bayesian_risk));
  return clamp01_100(round2(bayesian_risk));
}
 
function computeZTGrade(zero_trust_metric) {
  if (zero_trust_metric >= 85) return 'A';
  if (zero_trust_metric >= 70) return 'B';
  if (zero_trust_metric >= 55) return 'C';
  if (zero_trust_metric >= 40) return 'D';
  return 'E';
}
 
function formatRemarks(t) {
  return `TR=${t.transmission_rate} Mbps; EN=${t.energy_consumption} W; UA=${t.unauthorized_access_attempts}; RSSI=${t.signal_strength} dBm`;
}
 
module.exports = {
  computeBayesianRisk,
  computeZeroTrustMetric,
  computeZTGrade,
  formatRemarks,
};
 
 