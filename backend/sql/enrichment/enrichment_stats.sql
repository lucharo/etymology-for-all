SELECT status, COUNT(*) as count
FROM definitions_raw
GROUP BY status
