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
 */
ALTER TABLE
    page_impressions
ADD
    reverse_proxy_port smallint(5) unsigned NOT NULL
//
UPDATE
    page_impressions p
LEFT JOIN
    reverse_proxy_port rpp ON rpp.id = p.reverse_proxy_port_id
SET
    reverse_proxy_port = IF(
        reverse_proxy_port_id < 65535,
        COALESCE(rpp.port, 0),
        0
    )
//
ALTER TABLE
    page_impressions
DROP COLUMN
    reverse_proxy_port_id
//
DROP TABLE reverse_proxy_port
//
