<?php 
        
set_time_limit (300);

$lat = $_GET['lat'];
$lng = $_GET['lng'];

$theVarsStr = "$lat,$lng";
$filename = "backEnd/SiteInfoCreator.py";
$command = escapeshellcmd("python3 -O $filename $theVarsStr 2>&1");

$output = shell_exec($command);
if ($output)
{
    echo $output;
} else {
	echo "No backend response";
} 

?>