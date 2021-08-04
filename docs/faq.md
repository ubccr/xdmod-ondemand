
## The OnDemand realm does not show in the XDMoD portal

Make sure you are logged in with a user account that has either Center Director
or Center Staff role. Note the admin user account that is created with `xdmod-setup`
 does not have these roles by default.

## The xdmod-ondemand-ingestor command ran without error, but no data

Re-run the `xdmod-ondemand-ingestor` command with the `--debug` flag to show detailed information
about what it is running. Things to double check:
- The `webserver_format_str` setting matches the data format in the log files
- The filenames of the log files end in `.log` or `.log.N` where `N` is a number
- The url specified on the command line exactly matches the url in the webserver log files. This should include the protocol part (https://) and any port numbers but not the trailing forward slash character.
