<?php

namespace RegressionTests\Controllers;

use RegressionTests\TestHarness\RegressionTestHelper;

/**
 * Test the usage explorer for OnDemand realm regressions.
 */
class UsageExplorerOnDemandTest extends aUsageExplorerTest
{
    public function csvExportProvider()
    {
        $statistics = [
            'page_load_count',
            'session_count',
            'user_count',
            'app_count',
            'sessions_per_user'
        ];

        $groupBys = [
            'none',
            'person',
            'resource',
            'browser',
            'oodapplication',
            'ooduser',
            'operatingsys',
            'location'
        ];

        $settings = [
            'realm' => ['OnDemand'],
            'dataset_type' => ['aggregate', 'timeseries'],
            'statistic' => $statistics,
            'group_by' => $groupBys,
            'aggregation_unit' => ['Day', 'Month', 'Quarter', 'Year']
        ];

        return RegressionTestHelper::generateTests(
            $settings,
            '2021-01-12',
            '2021-01-12'
        );
    }
}
