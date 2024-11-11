---
title: Upgrade Guide
---

General Upgrade Notes
---------------------

The XDMoD OnDemand module should be upgraded at the same time as the main Open
XDMoD software. The upgrade procedure is documented on the [XDMoD upgrade
page](https://open.xdmod.org/upgrade.html). Downloads of RPMs and source
packages for the XDMoD OnDemand module are available from
[GitHub][github-latest-release].

11.0.0 Upgrade Notes
-------------------

Open XDMoD 11.0.0 fundamentally changes how page impressions, sessions, and
applications are counted and categorized, as described in detail in the
sections below. The changes only apply to newly ingested Open OnDemand web
server logs after upgrading to 11.0.0. If you have already ingested logs with a
prior version of Open XDMoD, those logs will not be able to be recounted and
recategorized using the new methods from 11.0.0 unless you still have copies of
the original log files, in which case you can delete the corresponding rows
from the `modw_ondemand.page_impressions` database table and reingest and
reaggregate the logs following the instructions below:

1. Back up the `modw_ondemand.page_impressions` database table (e.g., using
`mysqldump`).
1. Run the Bash loop below in the directory containing the log files to find
the earliest and latest timestamps in the logs:
    ```bash
    earliest=9999999999;
    latest=0;
    while read line; do
        current=$(date -d "$line" +"%s");
        if [ $current -lt $earliest ]; then
            earliest=$current;
        fi;
        if [ $current -gt $latest ]; then
            latest=$current;
        fi;
    done < <(cat *.log* | cut -d ']' -f 1 | cut -d '[' -f 2 | sed 's#/#-#g' | sed 's/:/ /');
    echo -e "Earliest: $earliest\nLatest: $latest"
    ```
1. Run the SQL command below to list the page impressions that will be deleted,
replacing `:earliest` with the earliest timestamp and `:latest` with the latest
timestamp obtained in the previous step:
    ```sql
    SELECT *
    FROM modw_ondemand.page_impressions
    WHERE log_time_ts BETWEEN :earliest AND :latest
    ```
1. If that is the correct list of page impressions you want to delete, run the
same SQL command from the previous step, replacing `SELECT *` with `DELETE`.
1. Reingest and reaggregate the logs following
[these instructions](ingestion-aggregation.md).

The sections below explain the details of the changes in 11.0.0.

### Using request path instead of Referer header

In previous versions, during ingestion of the Open OnDemand web server logs,
the Referer header of each line was used to determine which application was
being requested for that line. For example, take the following line from a web
server log file:

```
127.0.0.1 - sfoster [21/Feb/2024:22:30:56 +0000] "GET /pun/sys/dashboard/batch_connect/sys/jupyter/session_contexts/new HTTP/1.1" 200 13058 "https://resource.example.com/pun/sys/dashboard" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
```

In this example, the Referer header is
`https://localhost:3443/pun/sys/dashboard`, so prior to 11.0.0, this would be
counted as a request for the `sys/dashboard` application. However, the Referer
header actually indicates from which page the request originated, not the page
that is actually being requested. The actual application being requested on
this line is indicated by the request path,
`/pun/sys/dashboard/batch_connect/sys/jupyter/session_contexts/new`, which
would be the `sys/jupyter` application. In version 11.0.0, the request path is
now used to determine which application was being requested.

For more information on how applications are categorized, including
instructions for how to recategorize them, see
[this page](recategorizing-applications.md).

In order to enable parsing of the request path (and the request method, which
is not currently displayed in the XDMoD portal but is used for deduplication
and may be displayed in a future version), the `webserver_format_str` defined
in `portal_settings.d/ondemand.ini` must include either `%r` or both of `%m`
and `%U`.

11.0.0 also changes the criteria used for deduplicating page impressions. Prior
to 11.0.0, only the request time, user, and application were used. In 11.0.0,
the resource, request path, request method, reverse proxy host and port (if
applicable), browser geolocation (if applicable), browser family, and OS family
are also used to deduplicate page impressions.

### Removal of `-u` / `--url` option from `xdmod-ondemand-ingestor`

Prior to 11.0.0, logs would only be ingested if the Referer header matched the
value of the `-u` or `--url` option to `xdmod-ondemand-ingestor`. For example,
if the Referer header were `https://resource.example.com/pun/sys/dashboard`,
then the ingestor would only ingest the line if the `-u
https://resource.example.com` or `--url https://resource.example.com` option
were passed to `xdmod-ondemand-ingestor`. Now, the Referer header is not used,
so the `-u` / `--url` option is removed from `xdmod-ondemand-ingestor`. All
page impressions in the file(s) being ingested will be assigned to the resource
specified by the `-r` or `--resource` option to `xdmod-ondemand-ingestor`.

### Separation of ingestion and aggregation steps

Prior to 11.0.0, `xdmod-ondemand-ingestor` would always run both ingestion and
aggregation. In 11.0.0, ingestion and aggregation can now be run as separate
steps. The usage is explained on [this page](ingestion-aggregation.md).

### Inclusion of reverse proxy hosts and ports

In Open OnDemand, requests can be reverse proxied to other servers such as
Jupyter notebook servers, RStudio servers, VNC servers, etc. (details
[here](https://osc.github.io/ood-documentation/latest/how-tos/app-development/interactive/setup/enable-reverse-proxy.html)).
Prior to Open XDMoD 11.0.0, such requests were not counted in XDMoD. In 11.0.0,
such requests are now counted, and the reverse proxy host and port are
preserved in the `modw_ondemand.page_impressions` table (but the host and port
are not currently displayed in the XDMoD portal; they may be in a future
version).

### Exclusion of non page impressions

In 11.0.0, requests for app icons, images, stylesheets, scripts, datafiles,
etc. are not counted as page impressions unless they were being loaded from
the OnDemand "Files" or "File Editor" applications. Requests are only ingested
if the request path starts with `/pun/`, `/node/`, or `/rnode/`; the request is
from an authenticated user (i.e., not `"-"`); and the request is not for one of
the excluded file extensions from the list below (this is defined in the
configuration file `etl/etl_action_defs.d/ood/normalized.json`).

```
aff, css, dic, eot, gif, ico, jpeg, jpg, js, json, map, mp3, oga, ogg, otf, png, rstheme, svg, ttf, wasm, woff, woff2
```

### Removing `ihpc` from application names

Prior to 11.0.0, some applications were given a name with `(sys/ihpc)` at the
end. `iHPC` is an old name for interactive OnDemand apps; this name is no
longer used. In 11.0.0, page impressions that are ingested will no longer have
`(sys/ihpc)` in their application names. Applications for page impressions
that have already been ingested can be recategorized as explained on
[this page](recategorizing-applications.md).

### Speeding up person lookup

Prior to 11.0.0, each time ingestion was run, the ingestor would try to match
the username of all unknown people from the `modw_ondemand.page_impressions`
table with usernames from the `modw.systemaccount` table. 11.0.0 still does
this, but rather than doing so for all unknown people in the table, it only
does it for the page impressions that were ingested during the current run of
`xdmod-ondemand-ingestor`. This speeds up the overall ingestion.

### Allowing `@` in usernames

The `xdmod-ondemand-ingestor` now allows the `@` character to appear in
ingested usernames.

### Configuration File Changes

The upgrade renames `etl/etl_data.d/ood/application_map.json` to
`etl/etl_data.d/ood/application-map.json` and updates it with additional
application mappings. See [this page](recategorizing-applications.md) for
information on how to recategorize applications.

### Database Changes

During the upgrade, the `modw_ondemand.staging` table will have its
`header_referer` column removed and columns added for `request_method` and
`request_path`.

The `modw_ondemand.normalized` table will be truncated during the upgrade. It
will also receive new columns for `id` (which is now its primary key),
`request_path`, `request_method`, `reverse_proxy_host`, and
`reverse_proxy_port`. Its unique index will be updated to no longer include
`app` and to include `request_path`, `request_method`, `ua_family`, and
`ua_os_family`. In order to fit the new index, the `ua_family` and
`ua_os_family` columns are downsized from `VARCHAR(255)` to `VARCHAR(32)`.

During the upgrade, the `modw_ondemand.page_impressions` table will have its
`id` column updated to use `bigint(20) unsigned` instead of `int(11)` to be
able to accommodate more than 2,147,483,647 page impressions. It will also have
columns added for `request_path_id`, `request_method_id`,
`reverse_proxy_host_id`, and `reverse_proxy_port_id`. Its unique index will be
updated to remove `app_id` and to include `resource_id`, `request_path_id`,
`request_method_id`, `reverse_proxy_host_id`, `reverse_proxy_port_id`,
`app_id`, `location_id`, `ua_family_id`, and `ua_os_family_id`. Indexes will be
added to speed up aggregation, person lookup, and application recategorization.

If the `modw_ondemand.location` table has a row with `unknown` as its value for
`city`, `state`, and `country`; and `Unknown` as its value for `name`; the
upgrade will change the values for `city`, `state`, and `country` to `NA` for
that row.

The upgrade will add tables for `modw_ondemand.request_method`,
`modw_ondemand.request_path`, `modw_ondemand.reverse_proxy_host`, and
`modw_ondemand.reverse_proxy_port`.

During the upgrade, if the `modw_ondemand.location` table has a row with
`unknown` as its value for `city`, `state`, and `country`, these will be
replaced with the value `NA`.

11.0.1 Upgrade Notes
-------------------

## Configuration Changes

### Fix application map for noVNC requests

This release fixes the application mapping of page loads for OnDemand
applications launched via noVNC, specifically page loads whose request paths
are of this form:

```
/pun/sys/dashboard/noVNC-[version]/vnc.html?[params]&commit=Launch+[app]
```

Previously, these page loads were mapped to the `sys/dashboard` application.
This release fixes this to map them to the value of `[app]`. For example, a
page load with a request path that has the following form will be mapped to the
application `Desktop`:

```
/pun/sys/dashboard/noVNC-1.3.0/vnc.html?[params]&commit=Launch+Desktop
```

This new mapping will apply to any new page loads that are ingested into XDMoD.
For page loads that have already been ingested, the following SQL statements
can be run to remap them to the correct applications.

1. Make note of the timestamp when you started; this will be used later when
   reaggregating.
1. Lock the tables that will be updated:
    ```SQL
    LOCK TABLES
        modw_ondemand.app WRITE,
        modw_ondemand.request_path READ,
        modw_ondemand.page_impressions p1 WRITE,
        modw_ondemand.page_impressions p2 READ,
        modw_ondemand.request_path rp READ,
        modw_ondemand.app a READ
    ```
1. Insert the new rows into the `app` table if they do not already exist:
    ```SQL
    INSERT INTO modw_ondemand.app (app_path)
    SELECT REPLACE(
        REPLACE(
            REPLACE(
                REPLACE(
                    REPLACE(
                        REGEXP_REPLACE(
                            path,
                            '.*Launch\\+',
                            ''
                        ),
                        '+',
                        ' '
                    ),
                    '%28',
                    '('
                ),
                '%29',
                ')'
            ),
            '%2B',
            '+'
        ),
        '%2F',
        '/'
    )
    FROM modw_ondemand.request_path
    WHERE path LIKE '/pun/sys/dashboard/noVNC-%Launch+%'
    ON DUPLICATE KEY UPDATE app.id = app.id
    ```
1. Update the application mappings in the `page_impressions` table. Note
   that if you have many rows in the `page_impressions` table, it is
   recommended to do this in chunks, updating the values below of `BETWEEN 0
   AND 10000000` for each chunk:
    ```SQL
    UPDATE modw_ondemand.page_impressions p1
    JOIN (
        SELECT
            p2.id,
            REPLACE(
                REPLACE(
                    REPLACE(
                        REPLACE(
                            REPLACE(
                                REGEXP_REPLACE(
                                    path,
                                    '.*Launch\\+',
                                    ''
                                ),
                                '+',
                                ' '
                            ),
                            '%28',
                            '('
                        ),
                        '%29',
                        ')'
                    ),
                    '%2B',
                    '+'
                ),
                '%2F',
                '/'
            ) AS new_app_path
        FROM modw_ondemand.page_impressions p2
        JOIN modw_ondemand.request_path rp ON rp.id = p2.request_path_id
        WHERE rp.path LIKE '/pun/sys/dashboard/noVNC-%Launch+%'
        AND p2.id BETWEEN 0 AND 10000000
    ) p3 ON p3.id = p1.id
    JOIN modw_ondemand.app a ON a.app_path = p3.new_app_path
    SET p1.app_id = a.id
    ```
1. Unlock the tables:
    ```SQL
    UNLOCK TABLES
    ```
1. Reaggregate the page loads, replacing `YYYY-MM-DD HH:MM:SS` with the
   timestamp when you started:
    ```sh
    xdmod-ondemand-ingestor -a -m '[timestamp]'
    ```

### Fix request path filtering of File Editor page impressions

This release fixes the request path filter for categorizing page impressions
for requests of the OnDemand File Editor app. In 11.0.0, if a page impressions
had a request with a path of the following form:

```
/pun/sys/dashboard/files/edit/[path]
```

it would mistakenly map that to this request path instead:

```
/pun/sys/dashboard/files/[path]
```

This is fixed in 11.0.1 for any new page impressions that are ingested into
XDMoD. For page impressions that have already been ingested, the following SQL
statements can be run to remap them to the correct request paths.

1. Make sure to follow these steps when the automated ingestion and aggregation
   of OnDemand logs are NOT running.
1. First make a backup of the database, specifically the `modw_ondemand`
   schema, in case you need to recover it later.
1. Make note of the timestamp when you started; this will be used later when
   reaggregating.
1. Add the request path if it doesn't already exist:
    ```
    INSERT INTO modw_ondemand.request_path (path)
    VALUES ('/pun/sys/dashboard/files/edit/[path]');
    ```
   If a `Duplicate entry` error occurs, it just means the request path is
   already in the table; you can continue with the instructions below.
1. Set a variable for the request path ID:
    ```
    SET @request_path_id = (
        SELECT id
        FROM modw_ondemand.request_path
        WHERE path = '/pun/sys/dashboard/files/edit/[path]'
    );
    ```
1. Set the new request path ID, ignoring any rows that are now duplicates, and
   then delete the duplicates. Note that if you have many rows in the
   `page_impressions` table, it is recommended to do this in chunks, updating
   the values in the queries below of `BETWEEN 0 AND 10000000` for each chunk:
    ```
    UPDATE IGNORE modw_ondemand.page_impressions AS p
    JOIN modw_ondemand.request_path AS rp ON rp.id = p.request_path_id
    JOIN modw_ondemand.app AS a ON a.id = p.app_id
    SET p.request_path_id = @request_path_id
    WHERE rp.path = '/pun/sys/dashboard/files/[path]'
    AND a.app_path = 'sys/file-editor'
    AND p.id BETWEEN 0 AND 10000000;
    ```
    ```
    DELETE p FROM modw_ondemand.page_impressions AS p
    JOIN modw_ondemand.request_path AS rp ON rp.id = p.request_path_id
    JOIN modw_ondemand.app AS a ON a.id = p.app_id
    WHERE rp.path = '/pun/sys/dashboard/files/[path]'
    AND a.app_path = 'sys/file-editor'
    AND p.id BETWEEN 0 AND 10000000;
    ```
1. Reaggregate the changed page impressions by running the following command as
   the `xdmod` user, replacing `YYYY-MM-DD HH:MM:SS` with the timestamp when
   you started:
    ```sh
    xdmod-ondemand-ingestor -a -m YYYY-MM-DD HH:MM:SS
    ```

[github-latest-release]: https://github.com/ubccr/xdmod-ondemand/releases/latest
