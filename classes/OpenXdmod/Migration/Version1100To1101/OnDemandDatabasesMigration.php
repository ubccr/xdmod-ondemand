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
        $mysql_helper = MySQLHelper::factory($dbh);

        /* Fix how version 11.0.0 stored reverse proxy ports. This migration
         * only needs to be run if upgrading from a previous install of 11.0.0
         * to 11.0.1 (i.e., if the `reverse_proxy_port` table exists, since it
         * was created in the 10.5.0 to 11.0.0 migration). If upgrading from
         * 10.5.1 to 11.0.1 (i.e., if the `reverse_proxy_port` table does not
         * exist), the reverse proxy port storage is being newly introduced,
         * so there is no need to fix the old version because there is no old
         * version.
         */
        if ($mysql_helper->tableExists('modw_ondemand.reverse_proxy_port')) {
            Utilities::runEtlPipeline(
                ['migrate-page-impressions-11_0_0-11_0_1'],
                $this->logger
            );
        }
    }
}

