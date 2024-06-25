UPDATE modw_ondemand.location
SET
    city = 'NA',
    state = 'NA',
    country = 'NA'
WHERE city = 'unknown'
AND state = 'unknown'
AND country = 'unknown'
