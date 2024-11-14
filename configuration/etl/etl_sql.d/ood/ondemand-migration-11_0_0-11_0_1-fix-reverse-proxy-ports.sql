/* The `page_impressions.reverse_proxy_port_id` column is only `smallint(5)
 * unsigned`, but the `reverse_proxy_port.id` column is `int(11)`. This means
 * if `reverse_proxy_port.id` is > 65535 (the maximum value of `smallint(5)
 * unsigned`), then it will be mistakenly mapped as 65535 in
 * `page_impressions.reverse_proxy_port_id`.
 *
 * The port number does not need to be stored in a separate table. Thus, the
 * SQL below will create a new column `page_impressions.reverse_proxy_port`,
 * fill it with the corresponding value of `reverse_proxy_port.port` if
 * `page_impressions.reverse_proxy_port_id` < 65535 (otherwise 0), drop the
 * column `page_impressions.reverse_proxy_port_id`, and drop the table
 * `reverse_proxy_port`.
 *
 * This SQL is only run if the `reverse_proxy_port` column does not already
 * exist. If it does exist, that means XDMoD is being upgraded from 10.5.0 to
 * 11.0.1 and the column was created in the migration from 10.5.0 to 11.0.0,
 * which means the `reverse_proxy_port_id` column doesn't yet have any
 * data, in which case the remaining SQL is unnecessary.
 */

DELIMITER $$
IF NOT EXISTS(
    SELECT
        1
    FROM
        INFORMATION_SCHEMA.COLUMNS
    WHERE
        TABLE_SCHEMA = '${DESTINATION_SCHEMA}'
    AND
        TABLE_NAME = 'page_impressions'
    AND
        COLUMN_NAME = 'reverse_proxy_port'
)
BEGIN
    ALTER TABLE
        ${DESTINATION_SCHEMA}.page_impressions
    ADD
        reverse_proxy_port smallint(5) unsigned NOT NULL
    //
    UPDATE
        ${DESTINATION_SCHEMA}.page_impressions p
    LEFT JOIN
        ${DESTINATION_SCHEMA}.reverse_proxy_port rpp ON rpp.id = p.reverse_proxy_port_id
    SET
        reverse_proxy_port = IF(
            reverse_proxy_port_id < 65535,
            COALESCE(rpp.port, 0),
            0
        )
    //
    ALTER TABLE
        ${DESTINATION_SCHEMA}.page_impressions
    DROP COLUMN
        reverse_proxy_port_id
    //
    DROP TABLE reverse_proxy_port
    //
END
$$
DELIMITER //
