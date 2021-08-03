
The OnDemand module supports inferring geographic location based on the IP
address in the Open OnDemand logs. The IP address to location lookup uses
a GeoLite2 City binary database (MMDB) file, which is not supplied and must be downloaded
separately. 


The XDMoD OnDemand module has been tested with [MaxMind's free GeoLite2 City database](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data).

The MMDB file should be saved in a path that the `xdmod` user account has read
access.  The MMDB file is read by the process that loads information into XDMoD
datawarehouse.

An MMDB database file is only required for, and used by, the location lookup
when log data are loaded into XDMoD.  If no database file is available, then
the location information for all sessions will show as 'Unknown'. However
all of the other data dimensions are unaffected.
