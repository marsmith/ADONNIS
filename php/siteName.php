<?php 
                
$placeName = $_POST['placeName'];
$placeNameState = $_POST['placeNameState'];
$distanceNumber = $_POST['distanceNumber'];
$GNIS_NAME = $_POST['GNIS_NAME'];
$mouthOrOutlet = $_POST['mouthOrOutlet'];
$cardinalDir = $_POST['cardinalDir'];

$theVarsStr = "$placeName,$placeNameState,$distanceNumber,$GNIS_NAME,$mouthOrOutlet,$cardinalDir";

$command = escapeshellcmd("python3 ../py/findSiteName.py \"$theVarsStr\"");
$output = shell_exec($command);
echo json_encode($output);

?>