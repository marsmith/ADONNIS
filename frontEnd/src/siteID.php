<?php 
        
set_time_limit (300);

$lat = $_GET['lat'];
$lng = $_GET['lng'];

$theVarsStr = "$lat,$lng";

$command = escapeshellcmd("python -O ../../backEnd/SiteInfoCreator.py $theVarsStr 2>&1");
$output = shell_exec($command);
if ($output)
{
    echo $output;
} else {
    $command = escapeshellcmd("conda activate adonnis & python -O ../../backEnd/SiteInfoCreator.py $theVarsStr 2>&1");
    $output = shell_exec($command);
    echo $output;
}


?>