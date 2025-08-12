-- SCRIPT 1: RESET + SNAPSHOT 1
 
START TRANSACTION;
 
-- Delete previous risk/telemetry for only the named drones (supports space or underscore)
DELETE FROM drone_security_risk
WHERE device_id IN (
  SELECT device_id
  FROM trusted_device
  WHERE REPLACE(device_name, '_', ' ') IN ('Drone 1','Drone 2','Drone 3','Drone 4')
);
 
DELETE FROM drone_device_data
WHERE device_id IN (
  SELECT device_id
  FROM trusted_device
  WHERE REPLACE(device_name, '_', ' ') IN ('Drone 1','Drone 2','Drone 3','Drone 4')
);
 
-- Insert baseline telemetry (Snapshot 1)
INSERT INTO drone_device_data
(device_id, drone_name, transmission_rate, energy_consumption, unauthorized_access_attempts,
signal_strength, gps_location, resource_usage)
SELECT td.device_id, td.device_name, x.tr, x.en, x.ua, x.rssi, NULL,
       ROUND((x.tr * x.en)/10, 2) AS resource_usage
FROM trusted_device td
JOIN (
  SELECT 'drone1' AS name, 13.0 AS tr, 52.0 AS en, 2 AS ua,  -80.0 AS rssi
  UNION ALL SELECT 'drone2',       11.0,      49.0, 3,       -75.0
  UNION ALL SELECT 'drone3',        9.0,      55.0, 1,       -72.0
  UNION ALL SELECT 'dronesurv',       16.0,      58.0, 4,       -85.0
) x ON REPLACE(td.device_name, '_', ' ') = x.name;
 
-- Insert risk rows from latest telemetry per device (no window fn)
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