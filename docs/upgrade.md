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

Additional 11.0.0 Upgrade Notes
-------------------

Open XDMoD 11.0.0 fundamentally changes how page loads, sessions, and
applications are counted and categorized.

### Using request path instead of Referer header

In previous versions, during ingestion of the Open
OnDemand web server logs, the Referer header of each line was used to determine
which application was being requested for that line. For example, in the
following line from a web server log file:

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
would be the `sys/jupyter` application.

In version 11.0.0, the request path is now used to determine which application
was being requested. This changes how page loads, sessions, and applications
are counted. The changes will apply to any newly ingested log files, but not to
previously ingested log files. After upgrading, if you wish to apply the
changes to old logs that were ingested prior to 11.0.0, you will need to back
up the `modw_ondemand.page_impressions` database table (e.g., using
`mysqldump`), delete the old logs from the `modw_ondemand.page_impressions`
table, reingest the original web server log files, and reaggregate.

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
aff, css, dic, gif, ico, jpg, js, json, map, mp3, oga, ogg, otf, png, rstheme, svg, ttf, wasm, woff, woff2
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

[github-latest-release]: https://github.com/ubccr/xdmod-ondemand/releases/latest
