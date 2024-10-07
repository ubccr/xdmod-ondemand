<?php
/**
 * @author Joseph P. White
 */

namespace OpenXdmod\Setup;

use CCR\DB\MySQLHelper;
use CCR\Log;
use ETL\Utilities;

/**
 * Setup database schema for the Open OnDemand module.
 */
class OnDemandDbSetup extends DatabaseSetupItem
{

    /**
     * @inheritdoc
     */
    public function handle()
    {
        $conf = array(
            'console' => true,
            'consoleLogLevel' => Log::WARNING
        );

        $logger = Log::factory('xdmod-setup', $conf);

        $settings = $this->loadIniConfig('portal_settings');

        $this->console->displaySectionHeader('Open OnDemand module Setup');

        $this->console->displayMessage(<<<"EOT"
The Open OnDemand module stores information in the modw_ondemand
SQL database. This database must have the same access permissions
as the existing Open XDMoD databases.
EOT
        );
        $this->console->displayBlankLine();

        $this->console->displayMessage(<<<"EOT"
Please provide the password for the administrative account that will be
used to create the database.
EOT
        );
        $this->console->displayBlankLine();

        $adminUsername = $this->console->prompt(
            'DB Admin Username:',
            'root'
        );

        $adminPassword = $this->console->silentPrompt(
            'DB Admin Password:'
        );

        $xdmod_host = $this->console->prompt(
            'XDMoD Server name:',
            'xdmod.xdmod_default'
        );

        try {

            $sectionForDatabase = array(
                'modw_ondemand' => 'datawarehouse',
            );

            foreach ($sectionForDatabase as $database => $section) {
                $dbSettings = array(
                    'db_host' => $settings[$section . '_host'],
                    'db_port' => $settings[$section . '_port'],
                    'db_user' => $settings[$section . '_user'],
                    'db_pass' => $settings[$section . '_pass'],
                    'xdmod_host'=> $xdmod_host
                );

                $this->createDatabases(
                    $adminUsername,
                    $adminPassword,
                    $dbSettings,
                    array($database)
                );
            }

        } catch (Exception $e) {
            $this->console->displayBlankLine();
            $this->console->displayMessage('Failed to create databases:');
            $this->console->displayBlankLine();
            $this->console->displayMessage($e->getMessage());
            $this->console->displayBlankLine();
            $this->console->displayMessage($e->getTraceAsString());
            $this->console->displayBlankLine();
            $this->console->displayMessage('Settings file not saved!');
            $this->console->displayBlankLine();
            $this->console->prompt('Press ENTER to continue.');
            return;
        }

        Utilities::runEtlPipeline(
            array('bootstrap'),
            $logger,
            array(),
            'ondemand'
        );

        $aclConfig = new AclConfig($this->console);
        $aclConfig->handle();
    }
}
