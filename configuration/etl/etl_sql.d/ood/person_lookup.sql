UPDATE
    ${DESTINATION_SCHEMA}.page_impressions AS p
JOIN
    ${DESTINATION_SCHEMA}.users AS u ON u.id = p.user_id
JOIN
    ${UTILITY_SCHEMA}.systemaccount AS sa ON sa.username = u.username
SET
    p.person_id = sa.person_id
WHERE
    p.person_id = -1
AND
    p.last_modified >= ${LAST_MODIFIED}
AND
    p.resource_id = (
        SELECT
            rf.id
        FROM
            ${UTILITY_SCHEMA}.resourcefact AS rf
        WHERE
            rf.code = '${OOD_RESOURCE_CODE}'
    )
//
