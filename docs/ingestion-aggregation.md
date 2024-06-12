## Prerequisites:
1. The OnDemand module [installed](install.md)
2. The database schema has been [created](configuration.md#database-configuration)
3. The OnDemand resource has been [added](configuration.md#resource-setup)
4. The `portal_settings.d/ondemand.ini` configuration file [edited as needed](configuration.md#configuration-file)

## Ingest and Aggregate

The OnDemand weblog ingestion pipeline requires two parameters:

| Parameter Name | Description
| -------------- | -----------
| `-r` or `--resource` | Must be set to the name of the resource when it was added to XDMoD in the `xdmod-setup` command. |
| `-d` or `--dir` | Set to the path to a directory containing webserver log files from the Open OnDemand server. The ingestor will process all files in this directory that have the suffix `.log` or `.log.X` where X is a number |


The pipeline should be run as the `xdmod` user as follows:

    xdmod-ondemand-ingestor -d /path/to/ood_server_logs -r [resource]

The ingestion and aggregation pipelines can also be run independently of each other. To run only the ingestion pipeline, include the `-i` or `--ingest` parameter, e.g.:

    xdmod-ondemand-ingestor -d /path/to/ood_server_logs -r [resource] -i

The run only the aggregation pipeline, include the `-a` or `--aggregate` parameter along with the `-m` or `--last-modified-start-date` parameter. In this case the `-d` and `-r` parameters will be ignored. E.g.:

    xdmod-ondemand-ingestor -a -m '2024-01-01 00:00:00'

### Hints

For log files with a large amount of data (hundreds of thousands of lines), the ingestion pipeline
will use less memory and run faster if you split large log files into smaller ones. An example of how to do this
is to use the `split` commandline tool to split the large log file by lines and generate
output files with a numbered suffix (note the period at the end of the output filename):

```bash
split -d -l 20000 [LARGE INPUT FILE] /scratch/ondemand/webserver.log.
```
