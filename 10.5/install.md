## Prerequisites

The OnDemand module should be added to an existing working instance of
Open XDMoD version {{ page.version }} or later. See the [Open XDMoD site](https://open.xdmod.org/)
for setup and install instructions.

## Source code install

The source package is installed as follows:

    $ tar zxvf xdmod-ondemand-{{ page.sw_version }}.tar.gz
    $ cd xdmod-ondemand-{{ page.sw_version }}
    # ./install --prefix=/opt/xdmod

Change the prefix as desired. The default installation prefix is `/usr/local/xdmod`. These instructions assume you are installing Open XDMoD in `/opt/xdmod`.

## RPM install

    # yum install xdmod-ondemand-{{ page.sw_version }}-1.0.el7.noarch.rpm

## Next Step

[Configure](configuration.md) the package.
