function round2(n) { return Math.round(n * 100) / 100; }
function clamp01_100(n) { return Math.max(0, Math.min(100, n)); }
 
function computeBayesianRisk({ transmission_rate: tr, energy_consumption: en, unauthorized_access_attempts: ua, signal_strength: rssi }) {
  const part =
    5 * Math.max(0, tr - 10) +
    15 * ua +
    2 * Math.max(0, -70 - rssi) +
    2 * Math.max(0, en - 50);
  return Math.min(100, round2(part));
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
 
 