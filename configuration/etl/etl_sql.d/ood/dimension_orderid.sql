SET @row_number = 0
//
UPDATE 
    ${DESTINATION_SCHEMA}.location,
    (SELECT (@row_number:=@row_number + 1) AS order_id, id FROM ${DESTINATION_SCHEMA}.location ORDER BY city, state, country) tmp
SET
    ${DESTINATION_SCHEMA}.location.order_id = tmp.order_id
WHERE
     ${DESTINATION_SCHEMA}.location.id = tmp.id
//
UPDATE ${DESTINATION_SCHEMA}.location SET order_id = @row_number + 1 WHERE name = "Unknown"
//
