## Prerequisites

The OnDemand module should be added to an existing working instance of
Open XDMoD version {{ page.version }} or later. See the [Open XDMoD site](https://open.xdmod.org/)
for setup and install instructions.

## Source code install

The source package is installed as follows. Change the prefix to match the directory where Open XDMoD is installed.

    # tar zxvf xdmod-ondemand-{{ page.sw_version }}.tar.gz
    # cd xdmod-ondemand-{{ page.sw_version }}
    # ./install --prefix=/usr/local/xdmod

## RPM install

    # dnf install xdmod-ondemand-{{ page.sw_version }}-1.el8.noarch.rpm

## Next Step

[Configure](configuration.md) the package.
