<?php 
                
$placeName = $_POST['placeName'];
$placeNameState = $_POST['placeNameState'];
$distanceNumber = $_POST['distanceNumber'];
$GNIS_NAME = $_POST['GNIS_NAME'];
$mouthOrOutlet = $_POST['mouthOrOutlet'];
$cardinalDir = $_POST['cardinalDir'];

$theVarsStr = "$placeName,$placeNameState,$distanceNumber,$GNIS_NAME,$mouthOrOutlet,$cardinalDir";

$command = escapeshellcmd("python ../backEnd/Namer.py \"$theVarsStr\"");
$output = shell_exec($command);
if ($output)
{
    echo json_encode($output);
} else {
    $command = escapeshellcmd("conda activate adonnis & python ../backEnd/Namer.py \"$theVarsStr\"");
    $output = shell_exec($command);
    echo json_encode($output);
}

?>