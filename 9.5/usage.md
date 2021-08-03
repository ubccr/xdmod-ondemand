## Prerequisites:
1) The OnDemand module [installed](install.md)
2) The database schema has been [created](configuration.md#Database_Configuration)
3) The OnDemand resource has been [added](configuration.md#Resource_Setup)
4) The `portal_settings.d/ondemand.ini` configuration file [edited as needed](configuration.md#Configuration_file)

## Shred, Ingest, Aggregate

The OnDemand weblog ingestion pipeline requires three parameters:

| Parameter Name | Description
| -------------- | -----------
| `-r` or `--resource` | Must be set to the name of the resource when it was added to XDMoD in the `xdmod-setup` command. |
| `-u` or `--url` | Must be set to the hostname of the ondemand instance exactly as it appears in the server logs. This includes the `https://` parts and any port numbers but do not include the trailing forward slash. |
| `-d` or `--dir` | Set to the path to a directory containing webserver log files from the Open OnDemand server. The ingestor will process all files in this directory that have the suffix `.log` or `.log.X` where X is a number |


The pipeline should be run as the `xdmod` user as follows:

    xdmod-ondemand-ingestor -d /path/to/ood_server_logs -r [resource] -u [ondemand hostname]

### Hints

For log files with a large amount of data (hundreds of thousands of lines), the ingestion pipeline
will run faster if you split large log files into smaller ones. An example of how to do this
is to use the `split` commandline tool to split the large logf file by lines and generate
output files with a numbered suffix (note the period at the end of the output filename):

```bash
split -d -l 30000 [LARGE INPUT FILE] /scratch/ondemand/webserver.log.
```
