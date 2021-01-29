# XDMoD Open OnDemand Module

The XDMoD Open OnDemand Module is an optional module for
tracking usage of the Open OnDemand software in XDMoD.

For more information about Open OnDemand please visit
[the Open OnDemand website](https://openondemand.org/)

For more information, including information about additional Open XDMoD
capabilities provided as optional modules, please visit
[the Open XDMoD website](https://open.xdmod.org).

# Install and configuration.

The OnDemand module can use a GeoLite2 database to display location
information based on the IP address from the webserver logs. The IP to
location mapping is performed at data ingest time. The code has been
tested with [MaxMind's GeoLite2 City database](https://dev.maxmind.com/geoip/geoip2/geolite2/).

The database file is not distributed with Open XDMoD and must be
obtained seperately. If no database is present then all location
information will be marked as 'Unknown'. The database is not
required for the Open XDMoD module to display and process OnDemand 
server log data.

TODO: specify GeoIP data file location
TODO: specify webserver log file location


0) Add the `modw_ondemand` schema to the database.
1) Add a new resource to XDMoD using the XDMoD setup program. Resource type should be 'Gateway'.
2) run `xdmod-ingestor` to load the new resource into the database.

# Usage

Prerequisites:
1) Make sure you have added the OnDemand resource via `xdmod-setup` and run `xdmod-ingestor` to load the resource
   into XDMoD's datawarehouse.

To ingest the OnDemand weblogs. You need to specify the hostname of the ondemand instance exactly
as it appears in the server logs. This includes the `https://` parts and any port numbers but
do not include the trailing forward slash. You also need to specify the XDMoD resource name.
For example:

    /usr/share/xdmod/tools/etl/etl_overseer.php -p ondemand.ood-log-ingestion -d OOD_HOSTNAME=https://ondemand.ccr.buffalo.edu -d OOD_RESOURCE_CODE=ondemand -v debug
