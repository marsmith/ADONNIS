<?php 
                
$lat = $_POST['lat'];
$lng = $_POST['lng'];

$theVarsStr = "$lng,$lat";

$command = escapeshellcmd("python3 ../backEnd/GDALCode.py $theVarsStr");
$output = shell_exec($command);
echo json_encode($output);

?>