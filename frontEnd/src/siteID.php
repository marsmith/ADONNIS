<?php 
        
set_time_limit (300);

$lat = $_GET['lat'];
$lng = $_GET['lng'];

$theVarsStr = escapeshellcmd("$lat,$lng");
$filename = "backEnd/SiteInfoCreator.py";
$command = "python3 -O $filename $theVarsStr 2>&1";

$output = shell_exec($command);
if ($output && strcmp($output[0], "{") == 0)
{
    echo $output;
} else {
    $commandLocal = "conda activate ADONNIS & python -O $filename $theVarsStr 2>&1";
    $outputLocal = shell_exec($commandLocal);
    if ($outputLocal && strcmp($outputLocal[0], "{") == 0)
    {
        echo $outputLocal;
    } else {
        $fileExists = file_exists($filename);
        echo "Local format response is: $outputLocal from command: $commandLocal. Found file: $fileExists";
        echo "Server format response is: $output from command: $command. Found file: $fileExists";
    }
} 

?>