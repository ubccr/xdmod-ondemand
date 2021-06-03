#!/usr/bin/env expect
# Configure a test ondemand resource for a new XDMoD instanct

# Load helper functions
source [file join [file dirname [info script]] ../../../xdmod/tests/ci/scripts/helper-functions.tcl]

set timeout 240
spawn "xdmod-setup"

# Add an OnDemand resource
selectMenuOption 4

selectMenuOption 1
provideInput {Resource Name:} styx
provideInput {Formal Name:} {Open OnDemand Instance}
provideInput {Resource Type*} Gateway
provideInput {How many nodes does this resource have?} 0
provideInput {How many total processors (cpu cores) does this resource have?} 0

selectMenuOption s
confirmFileWrite yes
enterToContinue
confirmFileWrite yes
enterToContinue

# Setup the OnDemand database
selectMenuOption 9

selectMenuOption d

answerQuestion {DB Admin Username:} root
providePassword {DB Admin Password:} {}

provideInput {Do you want to see the output*} {no}

selectMenuOption q

selectMenuOption q

lassign [wait] pid spawnid os_error_flag value
exit $value
