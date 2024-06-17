XDMoD automatically categorizes page impressions by application. This
categorization is imperfect since it depends on pre-defined filters that are
not aware of all possible applications. After page impressions have been
ingested, you may wish to change their categorization. For example, they may
have been categorized as "Unknown" when you would be able to properly
categorize them manually given their request paths. For example, if you know
the request path `/node/[host]/[port]/foo/bar` matches the `foo` application,
you may wish to add a filter that assigns the `foo` application to any page
impressions with that request path, and apply that filter to all the previously
ingested page impressions without having to reingest the original log files.

To help with recategorization, as page impressions are ingested, their distinct
request paths are kept in the `modw_ondemand.request_path` database table, with
a `request_path_id` foreign key in the `modw_ondemand.page_impressions` fact
table. These can be used to recategorize previously ingested page
impressions by selecting all the page impressions that have certain request
paths and reassigning an application to them (instructions for doing this are
further down).

In the cases where multiple distinct request paths can be grouped together in a
general form without losing any relevant information (e.g., `/foo?a=b`,
`/foo?c=d`, and `/foo?e=f` might all be generalized as `/foo?[params]`), there
is a configuration file that filters request paths into general forms such that
they appear in the `modw_ondemand.request_path` table as, e.g.,
`/foo?[params]`. You may wish to recategorize groups of request paths into a
more general form to keep the size of this table smaller and to simplify the
query for recategorizing applications of a general form (instructions for
doing this are immediately below).

## Recategorizing future request paths

The file used for filtering request paths into more general forms is in the
configuration directory (whose location depends on how you configured your
installation, e.g., `/etc/xdmod`, `/opt/xdmod/etc`) under
`etl/etl_data.d/ood/request-path-filter.json`. This file contains a JSON object
whose keys are regular expressions used for matching against request paths from
the ingested logs, and whose values are the corresponding general forms that
will be stored in the database and assigned to future page impressions when
they are ingested. Edit this file to configure the filter how you wish.

If you have multiple OnDemand resources configured in XDMoD, you can also
filter request paths on a per-resource basis by having other similar files at
`etl/etl_data.d/ood/request-path-filter.d/${OOD_RESOURCE_CODE}.json`, where
`${OOD_RESOURCE_CODE}` matches the value passed via the `-r` argument to
`xdmod-ondemand-ingestor` (see the [ingestion and aggregation
instructions](ingestion-aggregation.md)). Any keys that are the same between
these files and the main `request-path-filter.json` will have their values
override the values in the main `request-path-filter.json`.

## Recategorizing existing request paths

To apply a new filter to page impressions that have already been ingested,
follow the instructions below to run some SQL statements in the XDMoD data
warehouse.

First you will want to back up the `modw_ondemand.page_impressions` and
`modw_ondemand.request_path` tables (e.g., using `mysqldump`) so that you can
restore the backups if something goes wrong that cannot be undone during these
steps.

Get the current timestamp prior to running any statements. Save this timestamp
somewhere. Later, you will use it when you re-aggregate all page impressions
modified after it.

```sql
SELECT CURRENT_TIMESTAMP();
```

Set some variables that will be used in subsequent statements. Replace the
values below; set the desired regex from the filter and the desired generalized
request path. Be careful that if the regex from the filter contains a grouping
that gets backreferenced in the general form (e.g., `$1`) that you only run all
these instructions for one member of the grouping at a time (e.g., if the regex
is `a/(b|c|d)/e` and the general form is `a/[foo]/e`, make sure to run all
these instructions once with the filter set to `a/b/e`, once with it set to
`a/c/e`, and once with it set to `a/d/e`):

```sql
SET @request_path_filter = '^/rnode/[^/]+/[^/]+(/data/plugin/images/images\\?).+';
SET @general_request_path = '/rnode/[host]/[port]/data/plugin/images/images?[params]';
```

Set locks for the tables you will be modifying, so that the automatic ingestion
pipeline does not try to modify the tables at the same time you are:

```sql
LOCK TABLES
modw_ondemand.page_impressions WRITE,
modw_ondemand.page_impressions AS p WRITE,
modw_ondemand.request_path WRITE,
modw_ondemand.request_path AS rp READ;
```

Insert the new request path into `modw_ondemand.request_path` table and get its
ID:

```sql
INSERT INTO modw_ondemand.request_path (path)
VALUES (@general_request_path);
SET @request_path_id = (
    SELECT id
    FROM modw_ondemand.request_path
    WHERE path = @general_request_path
);
```

If a `Duplicate entry` error occurs, it just means the request path is already
in the table; you can continue with the instructions below.

Create a temporary table containing all the page impressions whose path matches
the filter but which don't already have the general form:

```sql
CREATE TEMPORARY TABLE modw_ondemand.tmp_request_path_updates AS SELECT p.*, rp.path
FROM modw_ondemand.page_impressions AS p
JOIN modw_ondemand.request_path AS rp ON rp.id = p.request_path_id
WHERE rp.path REGEXP @request_path_filter
AND rp.path != @general_request_path;
```

Select all the rows from the temporary table and confirm it is a correct list
of page impressions whose request path should be set to the general form:

```sql
SELECT * FROM modw_ondemand.tmp_request_path_updates;
```

Then, set the corresponding new `request_path_id` in the `page_impressions`
table, ignoring any rows that are now duplicates:

```sql
UPDATE IGNORE modw_ondemand.tmp_request_path_updates AS t
JOIN modw_ondemand.page_impressions AS p ON p.id = t.id
SET p.request_path_id = @request_path_id;
```

Confirm it worked, noting that some rows may not have been updated because they
are now duplicates of other rows:

```sql
SELECT p.*, rp.path
FROM modw_ondemand.page_impressions AS p
JOIN modw_ondemand.request_path AS rp ON rp.id = p.request_path_id
WHERE rp.path REGEXP @request_path_filter;
```

Select any rows that are duplicates:

```sql
SELECT p.*, rp.path
FROM modw_ondemand.page_impressions AS p
JOIN modw_ondemand.request_path AS rp ON rp.id = p.request_path_id
WHERE rp.path REGEXP @request_path_filter
AND rp.path != @general_request_path;
```

And delete those:

```sql
DELETE p
FROM modw_ondemand.page_impressions AS p
JOIN modw_ondemand.request_path AS rp ON rp.id = p.request_path_id
WHERE rp.path REGEXP @request_path_filter
AND rp.path != @general_request_path;
```

Confirm it worked:

```sql
SELECT p.*, rp.path
FROM modw_ondemand.page_impressions AS p
JOIN modw_ondemand.request_path AS rp ON rp.id = p.request_path_id
WHERE rp.path REGEXP @request_path_filter;
```

And drop the temporary table:

```sql
DROP TABLE modw_ondemand.tmp_request_path_updates;
```

Mark all the page impressions that have the general form as being modified
so they can be reaggregated later:

```sql
UPDATE modw_ondemand.page_impressions
SET last_modified = CURRENT_TIMESTAMP()
WHERE request_path_id = @request_path_id;
```

Next, select the rows from the `request_path` table that match the filter:

```sql
SELECT *
FROM request_path
WHERE path REGEXP @request_path_filter
AND id != @request_path_id;
```

If those rows look correct to delete, run the SQL statement below to delete
them (the same statement as immediately above but replacing `SELECT *` with
`DELETE`).

```sql
DELETE
FROM request_path
WHERE path REGEXP @request_path_filter
AND id != @request_path_id;
```

Finally, unlock the tables:

```sql
UNLOCK TABLES;
```

## Recategorizing future applications

The file used for mapping applications is in the configuration directory (whose
location depends on how you configured your installation, e.g., `/etc/xdmod`,
`/opt/xdmod/etc`) under `etl/etl_data.d/ood/application-map.json`. This
file contains a JSON object whose keys are regular expressions used for
matching against request paths from the ingested logs, and whose values are the
corresponding applications that will be stored in the database and assigned to
future page impressions when they are ingested. Edit this file to configure the
application map how you wish.

If you have multiple OnDemand resources configured in XDMoD, you can also
map applications on a per-resource basis by having other similar files at
`etl/etl_data.d/ood/application-map.d/${OOD_RESOURCE_CODE}.json`, where
`${OOD_RESOURCE_CODE}` matches the value passed via the `-r` argument to
`xdmod-ondemand-ingestor` (see the [ingestion and aggregation
instructions](ingestion-aggregation.md)). Any keys that are the same between
these files and the main `application-map.json` will have their values
override the values in the main `application-map.json`.

## Recategorizing existing applications

To recategorize applications for page impressions that have already been
ingested, follow the instructions below to run some SQL statements in the XDMoD
data warehouse.

First you will want to back up the `modw_ondemand.page_impressions` and
`modw_ondemand.app` tables (e.g., using `mysqldump`) so that you can
restore the backups if something goes wrong that cannot be undone during these
steps.

Get the current timestamp prior to running any statements (if you already did
this above when recategorizing request paths, keep that one instead). Save this
timestamp somewhere. Later, you will use it when you re-aggregate all page
impressions modified after it.

```sql
SELECT CURRENT_TIMESTAMP();
```

Get the list of all apps so you can get the IDs of the app whose ID you want
to change and the ID of the app to which you want to change it.

```sql
SELECT *
FROM modw_ondemand.app;
```

Set some variables that will be used in subsequent statements. Set
`@request_path_filter` to a regex that will be used to match page impressions
whose request paths have a general form. Set `@old_app_id` to the current app
ID of the page impressions you want to change. Set `@new_app_id` to the ID of
the app to which you want to change them.

```sql
SET @request_path_filter = '^/rnode/[^/]+/[^/]+/(proxy/[^/]+/)?(data|experiment)/.*';
SET @old_app_id = 8;
SET @new_app_id = 7;
```

Get the list of page impressions that will be changed:

```sql
SELECT *
FROM modw_ondemand.page_impressions AS p
JOIN modw_ondemand.request_path AS rp ON rp.id = p.request_path_id
JOIN modw_ondemand.app AS a ON a.id = p.app_id
WHERE p.app_id = @old_app_id
AND rp.path REGEXP @request_path_filter;
```

Set locks for the tables you will be modifying, so that the automatic ingestion
pipeline does not try to modify the tables at the same time you are:

```sql
LOCK TABLES
modw_ondemand.page_impressions AS p WRITE,
modw_ondemand.request_path AS rp READ,
modw_ondemand.app AS a READ;
```

If the list is correct, change the app ID from old to new:

```sql
UPDATE modw_ondemand.page_impressions AS p
JOIN modw_ondemand.request_path AS rp ON rp.id = p.request_path_id
SET p.app_id = @new_app_id
WHERE p.app_id = @old_app_id
AND rp.path REGEXP @request_path_filter;
```

Confirm it worked:

```sql
SELECT *
FROM modw_ondemand.page_impressions AS p
JOIN modw_ondemand.request_path AS rp ON rp.id = p.request_path_id
JOIN modw_ondemand.app AS a ON a.id = p.app_id
WHERE p.app_id = @new_app_id
AND rp.path REGEXP @request_path_filter;
```

And unlock the tables:

```sql
UNLOCK TABLES;
```

## Reaggregating

After you have run all the SQL statements, use the `xdmod-ondemand-ingestor`
shell command to re-aggregate all of the page impressions that were modified
after the value for `CURRENT_TIMESTAMP()` that you obtained above (replace
`'2024-05-09 14:10:33'` in the example below):

```sh
xdmod-ondemand-ingestor -a -m '2024-05-09 14:10:33'
```

