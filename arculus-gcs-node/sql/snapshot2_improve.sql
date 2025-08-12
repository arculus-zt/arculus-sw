-- SCRIPT 2: SNAPSHOT 2 (improve security posture -> higher ZT grades)
 
START TRANSACTION;
 
-- Insert improved telemetry values
INSERT INTO drone_device_data
(device_id, drone_name, transmission_rate, energy_consumption, unauthorized_access_attempts,
signal_strength, gps_location, resource_usage)
SELECT td.device_id, td.device_name, x.tr, x.en, x.ua, x.rssi, NULL,
       ROUND((x.tr * x.en)/10, 2)
FROM trusted_device td
JOIN (
  SELECT 'drone1' AS name, 10.0 AS tr, 45.0 AS en, 0 AS ua,  -68.0 AS rssi
  UNION ALL SELECT 'drone2',       12.0,      49.0, 1,       -72.0
  UNION ALL SELECT 'drone3',       10.0,      45.0, 0,       -69.0
  UNION ALL SELECT 'dronesurv',       12.0,      50.0, 1,       -74.0
) x ON REPLACE(td.device_name, '_', ' ') = x.name;
 
-- Insert new risk rows from newest telemetry (no window fn)
INSERT INTO drone_security_risk
(device_id, drone_name, bayesian_risk, attack_type, zero_trust_metric, zt_grade, remarks)
SELECT
  d.device_id,
  d.drone_name,
  LEAST(100,
    ROUND(
      5*GREATEST(0, d.transmission_rate - 10)
    + 15*d.unauthorized_access_attempts
    + 2*GREATEST(0, -70 - d.signal_strength)
    + 2*GREATEST(0, d.energy_consumption - 50), 2)
  ) AS bayesian_risk,
  CASE
    WHEN d.unauthorized_access_attempts >= 4 THEN 'Faker'
    WHEN d.transmission_rate >= 16 THEN 'Flooder'
    WHEN d.signal_strength <= -85 OR d.energy_consumption >= 58 THEN 'Physical Capture'
    ELSE 'Faker'
  END AS attack_type,
  ROUND(
    GREATEST(0, LEAST(100, 100 - (
      5*GREATEST(0, d.transmission_rate - 10)
    + 15*d.unauthorized_access_attempts
    + 2*GREATEST(0, -70 - d.signal_strength)
    + 2*GREATEST(0, d.energy_consumption - 50)
  ))), 2) AS zero_trust_metric,
  CASE
    WHEN (100 - (
      5*GREATEST(0, d.transmission_rate - 10)
    + 15*d.unauthorized_access_attempts
    + 2*GREATEST(0, -70 - d.signal_strength)
    + 2*GREATEST(0, d.energy_consumption - 50)
  )) >= 85 THEN 'A'
    WHEN (100 - (
      5*GREATEST(0, d.transmission_rate - 10)
    + 15*d.unauthorized_access_attempts
    + 2*GREATEST(0, -70 - d.signal_strength)
    + 2*GREATEST(0, d.energy_consumption - 50)
  )) >= 70 THEN 'B'
    WHEN (100 - (
      5*GREATEST(0, d.transmission_rate - 10)
    + 15*d.unauthorized_access_attempts
    + 2*GREATEST(0, -70 - d.signal_strength)
    + 2*GREATEST(0, d.energy_consumption - 50)
  )) >= 55 THEN 'C'
    WHEN (100 - (
      5*GREATEST(0, d.transmission_rate - 10)
    + 15*d.unauthorized_access_attempts
    + 2*GREATEST(0, -70 - d.signal_strength)
    + 2*GREATEST(0, d.energy_consumption - 50)
  )) >= 40 THEN 'D'
    ELSE 'E'
  END AS zt_grade,
  CONCAT('TR=', d.transmission_rate, ' Mbps; EN=', d.energy_consumption,
         ' W; UA=', d.unauthorized_access_attempts,
         '; RSSI=', d.signal_strength, ' dBm') AS remarks
FROM drone_device_data d
JOIN (
  SELECT device_id, MAX(data_id) AS max_data_id
  FROM drone_device_data
  GROUP BY device_id
) m ON m.device_id = d.device_id AND m.max_data_id = d.data_id
WHERE REPLACE(d.drone_name, '_', ' ') IN ('drone1','drone2','drone3','dronesurv');
 
COMMIT;
