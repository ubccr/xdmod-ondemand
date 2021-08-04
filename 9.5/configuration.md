
## Prerequisites

The OnDemand module must be [installed](install.md). Optionally a GeoLite2
geolocation database file can be [installed](requirements.md).

## Database Configuration

### Interactive script configuration

The Open OnDemand XDMoD module adds an additional menu item to the XDMoD interactive setup software. Run the script as follows:

    # xdmod-setup

and select the ‘Open OnDemand’ option in the main menu. The Open OnDemand
section only has a single option: setup the database.  This option creates the
necessary database schema in the XDMoD
datawarehouse. You will need to provide the credentials for your MySQL root
user, or another user that has privileges to create databases. A single
database `modw_ondemand` will be created.  The database user that is
specified in the `portal_settings.ini` will be granted access to this
database.

### Manual configuration

If the database server is located on a different host than the webserver then it is necessary
to setup the database manually.

Create a database schema called `modw_ondemand` and grant permission for the XDMoD database user
account to access this schema.

Once the schema is created then the `acl-config` command should be run:

    $ /usr/xdmod/bin/acl-config

## Resource Setup

Add a new resource to Open XDMoD using the `xdmod-setup` script.
Instructions for adding the resource are on the [main Open XDMoD page](https://open.xdmod.org/9.5/configuration.html#resources)

The Open OnDemand resource must have a type set to `gateway`.

The resource setup menu will prompt for the node and core count for the resource. These
data are not currently used by the On Demand module, but it is recommmended to use the
correct core and node counts for the Open OnDemand webserver for consistency.

**The `xdmod-ingestor` script must be run after the new resource is added**. Running
`xdmod-ingestor` loads the resource information into the XDMoD datawarehouse.

## Configuration file

The `/etc/xdmod/portal_settings.d/ondemand.ini` configuration
file settting are listed below:

| Parameter Name |  Description
| -------------- | -----------
| `geoip_database`       | Full path to the GeoLite2 City file (in MMDB format). Set this to an empty string if no file is available (location data in XDMoD will show as Unknown). |
| `webserver_format_str` | The format string for the webserver access logs. This should be set to the same value as the `LogFormat` directive in the apache server for the Open OnDemand instance |

