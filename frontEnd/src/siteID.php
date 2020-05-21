<?php 
        
set_time_limit (300);

$lat = $_POST['lat'];
$lng = $_POST['lng'];

$theVarsStr = "$lat,$lng";

$command = escapeshellcmd("python -O ../../backEnd/SiteInfoCreator.py $theVarsStr 2>&1");
$output = shell_exec($command);
if ($output)
{
    echo json_encode($output);
} else {
    $command = escapeshellcmd("conda activate adonnis & python -O ../../backEnd/SiteInfoCreator.py $theVarsStr 2>&1");
    $output = shell_exec($command);
    echo json_encode($output);
}


?>