## Prerequisites

The OnDemand module should be added to an existing working instance of Open
XDMoD. See the [Open XDMoD site](https://open.xdmod.org/) for setup and install
instructions.

## RPM Installation

The RPM package can be downloaded from [GitHub](https://github.com/ubccr/xdmod-ondemand/releases/tag/v{{ page.rpm_version }}).

    # dnf install xdmod-ondemand-{{ page.rpm_version }}.el8.noarch.rpm

## Source Installation

The source package can be downloaded from
[GitHub](https://github.com/ubccr/xdmod-ondemand/releases/tag/v{{ page.rpm_version }}).
Make sure to download `xdmod-ondemand-{{ page.sw_version }}.tar.gz`, not the
GitHub-generated "Source code" files.

**NOTE**: The installation prefix must be the same as your existing Open
XDMoD installation. These instructions assume you have already installed
Open XDMoD in `/opt/xdmod-{{ page.sw_version }}`.

    # tar zxvf xdmod-ondemand-{{ page.sw_version }}.tar.gz
    # cd xdmod-ondemand-{{ page.sw_version }}
    # ./install --prefix=/opt/xdmod-{{ page.sw_version }}

## Next Step

[Configure](configuration.md) the package.
