<?php

namespace OpenXdmod\Migration\Version1100To1101;

use OpenXdmod\Migration\DatabasesMigration as AbstractDatabasesMigration;
use CCR\DB;
use CCR\DB\MySQLHelper;
use ETL\Utilities;

class OnDemandDatabasesMigration extends AbstractDatabasesMigration
{
    public function execute()
    {
        parent::execute();

        $dbh = DB::factory('datawarehouse');
        $mysqlHelper = MySQLHelper::factory($dbh);

        /* Fix bugs introduced in 11.0.0. This does not need to be done for
         * upgrades from 10.5.1 -> 11.0.0 -> 11.0.1, since there will have
         * been no ingestion done in between upgrading from 10.5.1 -> 11.0.0
         * and upgrading from 11.0.0 -> 11.0.1. The way to detect this is the
         * presence of the `reverse_proxy_port` table whose definition was
         * added in 11.0.0 but then removed in 11.0.1. However, if someone
         * previously upgraded from 10.5.0 to 11.0.0 and ran ingestion, those
         * ingested logs need to be fixed, which they will be here.
         */
        if ($mysqlHelper->tableExists('modw_ondemand.reverse_proxy_port')) {
            $startTime = date('Y-m-d H:i:s');
            Utilities::runEtlPipeline(
                ['migrate-page-impressions-11_0_0-11_0_1'],
                $this->logger,
                [],
                'ondemand'
            );
            Utilities::runEtlPipeline(
                ['aggregation'],
                $this->logger,
                ['last-modified-start-date' => $startTime],
                'ondemand'
            );
        }
    }
}

