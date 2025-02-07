<?php

namespace RegressionTests\Controllers;

use RegressionTests\Controllers\MetricExplorerChartsTest;

class MetricExplorerOnDemandChartsTest extends MetricExplorerChartsTest
{
    protected static function getFilterTestBaseConfig()
    {
        return [
            [
                'realm' => 'OnDemand',
                'metric' => 'sessions_per_user',
                'date' => '2021-01-12'
            ]
        ];
    }
}
