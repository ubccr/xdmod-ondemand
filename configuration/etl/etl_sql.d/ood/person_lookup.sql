UPDATE
    ${DESTINATION_SCHEMA}.page_impressions p, ${DESTINATION_SCHEMA}.users u, ${UTILITY_SCHEMA}.systemaccount sa
SET
    p.person_id = sa.person_id
WHERE
    p.user_id = u.id AND sa.username = u.username AND p.person_id = -1
//
