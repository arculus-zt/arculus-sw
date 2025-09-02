START TRANSACTION;
 
DELETE FROM drone_security_risk

WHERE device_id IN (

  SELECT device_id FROM trusted_device

  WHERE REPLACE(device_name, '_', ' ') IN ('Drone 1','Drone 2','Drone 3','Drone 4')

);
 
DELETE FROM drone_device_data

WHERE device_id IN (

  SELECT device_id FROM trusted_device

  WHERE REPLACE(device_name, '_', ' ') IN ('Drone 1','Drone 2','Drone 3','Drone 4')

);
 
COMMIT;

 