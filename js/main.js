var map;
var marker;
var preexistingSiteLayer;
var highlightedStreamsLayer;
var firstpolyline;
var printURL = "";
var currStationName = "";
var counter = 0;

var queryingStreams = false;
var currentQueriedStreams;

var collectedData = {
	placeName: "",
	placeNameState: "",
	distanceNumber: undefined,
	GNIS_NAME: "",
	mouthOrOutlet: "",
	cardinalDir: ""
};

var closestPoint;
var globFeature;
var globSmallestDistIndex;
function toRadian(num) {
    return num * (Math.PI / 180);
}

function toDegree(num) {
    return num * (180 / Math.PI);
}

function deg_to_dms (dd) {
	var beg_sign = ""
	if (dd < 0){
	  beg_sign = "0";
	}
	var absDd = Math.abs(dd);
	var deg = absDd | 0;
	var frac = absDd - deg;
	var min = (frac * 60) | 0;
	var sec = frac * 3600 - min * 60;
	// Round it to 2 decimal points.
	sec = Math.round(sec * 100) / 100;
	seconds = sec.toString();
	seconds = seconds.split('.');
	return [beg_sign + deg + ""+ min + "" + seconds[0], seconds[1]];

   }

function getHorizontalBearing(fromLat, fromLon, toLat, toLon) {
    fromLat = toRadian(fromLat);
    fromLon = toRadian(fromLon);
    toLat = toRadian(toLat);
    toLon = toRadian(toLon);

    let dLon = toLon - fromLon;
    let x = Math.tan(toLat / 2 + Math.PI / 4);
    let y = Math.tan(fromLat / 2 + Math.PI / 4);
    let dPhi = Math.log(x / y);
    if (Math.abs(dLon) > Math.PI) {
        if (dLon > 0.0) {
            dLon = -(2 * Math.PI - dLon);
        } else {
            dLon = (2 * Math.PI + dLon);
        }
    }

    return (toDegree(Math.atan2(dLon, dPhi)) + 360) % 360;
}

function getBoundingBox(centerPoint, distance) {
	var MIN_LAT, MAX_LAT, MIN_LON, MAX_LON, R, radDist, degLat, degLon, radLat, radLon, minLat, maxLat, minLon, maxLon, deltaLon;
	if (distance < 0) {
	  return 'Illegal arguments';
	}
	// helper functions (degrees<–>radians)
	Number.prototype.degToRad = function () {
	  return this * (Math.PI / 180);
	};
	Number.prototype.radToDeg = function () {
	  return (180 * this) / Math.PI;
	};
	// coordinate limits
	MIN_LAT = (-90).degToRad();
	MAX_LAT = (90).degToRad();
	MIN_LON = (-180).degToRad();
	MAX_LON = (180).degToRad();
	// Earth's radius (km)
	R = 6378.1;
	// angular distance in radians on a great circle
	radDist = distance / R;
	// center point coordinates (deg)
	degLat = centerPoint[0];
	degLon = centerPoint[1];
	// center point coordinates (rad)
	radLat = degLat.degToRad();
	radLon = degLon.degToRad();
	// minimum and maximum latitudes for given distance
	minLat = radLat - radDist;
	maxLat = radLat + radDist;
	// minimum and maximum longitudes for given distance
	minLon = void 0;
	maxLon = void 0;
	// define deltaLon to help determine min and max longitudes
	deltaLon = Math.asin(Math.sin(radDist) / Math.cos(radLat));
	if (minLat > MIN_LAT && maxLat < MAX_LAT) {
	  minLon = radLon - deltaLon;
	  maxLon = radLon + deltaLon;
	  if (minLon < MIN_LON) {
		minLon = minLon + 2 * Math.PI;
	  }
	  if (maxLon > MAX_LON) {
		maxLon = maxLon - 2 * Math.PI;
	  }
	}
	// a pole is within the given distance
	else {
	  minLat = Math.max(minLat, MIN_LAT);
	  maxLat = Math.min(maxLat, MAX_LAT);
	  minLon = MIN_LON;
	  maxLon = MAX_LON;
	}
	return L.latLngBounds(L.latLng(maxLat.radToDeg(), maxLon.radToDeg()), L.latLng(minLat.radToDeg(), minLon.radToDeg()));
	/* return [
	  minLon.radToDeg(),
	  minLat.radToDeg(),
	  maxLon.radToDeg(),
	  maxLat.radToDeg()
	]; */
}

function getDistanceKM (lat1, lng1, lat2, lng2){
	
}

function getSpPoint(A,B,C){
    var x1=A.x, y1=A.y, x2=B.x, y2=B.y, x3=C.x, y3=C.y;
    var px = x2-x1, py = y2-y1, dAB = px*px + py*py;
    var u = ((x3 - x1) * px + (y3 - y1) * py) / dAB;
    var x = x1 + u * px, y = y1 + u * py;
    return {x:x, y:y}; //this is D
}

function calcIsInsideLineSegment(line1, line2, pnt) {
    var L2 = ( ((line2.x - line1.x) * (line2.x - line1.x)) + ((line2.y - line1.y) * (line2.y - line1.y)) );
    if(L2 == 0) return false;
    var r = ( ((pnt.x - line1.x) * (line2.x - line1.x)) + ((pnt.y - line1.y) * (line2.y - line1.y)) ) / L2;

    return (0 <= r) && (r <= 1);
}

function distance(lat1, lon1, lat2, lon2, unit = 'K') {
	if ((lat1 == lat2) && (lon1 == lon2)) {
		return 0;
	}
	else {
		var radlat1 = Math.PI * lat1/180;
		var radlat2 = Math.PI * lat2/180;
		var theta = lon1-lon2;
		var radtheta = Math.PI * theta/180;
		var dist = Math.sin(radlat1) * Math.sin(radlat2) + Math.cos(radlat1) * Math.cos(radlat2) * Math.cos(radtheta);
		if (dist > 1) {
			dist = 1;
		}
		dist = Math.acos(dist);
		dist = dist * 180/Math.PI;
		dist = dist * 60 * 1.1515;
		if (unit=="K") { dist = dist * 1.609344 }
		if (unit=="N") { dist = dist * 0.8684 }
		return dist;
	}
}

function changeChosenSiteName() {
	var chosenName = $('#SuggestedNames').find(":selected").text();
	currStationName = chosenName;
	$("#printThis").html('<iframe src="' + printURL + '&stationName=' + currStationName + '" style="display:none;" name="frame" id="theIframe"></iframe>');
}

function on() {
	//document.getElementById("overlay").style.display = "block";
	$('#myModal').on('shown.bs.modal', function () {

		var progress = setInterval(function() {
		var $bar = $('.bar');

		if ($bar.width()>=500) {

			// complete
			showFoundData();
			clearInterval(progress);
			$('.progress').removeClass('active');
			$('#myModal').modal('hide');
			$bar.width(0);

		}
		else {

			// perform processing logic here
			$bar.width(0);
			$bar.width(counter*5);
		}

		$bar.text(($bar.width()/5) + "%");
		}, 800);


	})
	$('#myModal').modal('show');

}

function off() {
	//document.getElementById("overlay").style.display = "none";
	$('#myModal').on('hide.bs.modal', function () {

		var progress = setInterval(function() {
		var $bar = $('.bar');
		clearInterval(progress);

		$bar.width(0);

		$bar.text(0 + "%");
		}, 800);

	})
	$('#myModal').modal('hide');
	counter = 0;
}

function callAjaxCalls(e) {
	$.when(ajaxHUCInfo(e), ajaxContrDrainageArea(e), ajaxTimeZoneCode(e), ajaxAltitude(e), ajaxCountryCode(e), ajaxCountyStateFIPS(e), ajaxNearbyPlace(e)).done(function(a1, a2, a3, a4, a5, a6, a7){
		$.when(ajaxSiteName(), ajaxSiteID()).done(function(a8, a9){
			//showFoundData();
		});
	});
}

function showFoundData() {
	off();
	console.log(collectedData);
	$('#siteData').modal('show');
	var siteNamesString = "";
	for (const siteName of collectedData.suggSiteNames.Results) {
		siteNamesString += "<option>" + siteName + "</option>";
	}
	$("#SuggestedNames").html(siteNamesString);
	$("#SiteID").val(collectedData.siteID);
	$("#Alt").val(collectedData.altitude);
	$("#CC").val(collectedData.countryCode);
	$("#TimeZone").val(collectedData.timeZoneCode);
	$("#Drain").val(collectedData.contrDrainageArea);
	$("#HUC").val(collectedData.HUC);
	$("#HUCN").val(collectedData.HUCName);
	$("#State").val(collectedData.state);
	$("#County").val(collectedData.county);
	$("#StateFIPS").val(collectedData.stateFIPS);
	$("#CountyFIPS").val(collectedData.countyFIPS);


	var latDMS = deg_to_dms(collectedData.coords.lat);
	var lngDMS = deg_to_dms(collectedData.coords.lng);
	altDec = (collectedData.altitude).toString();
	altDec = altDec.split(".")[1];
	countyCode = collectedData.countyFIPS.toString();
	countyCode = countyCode.slice(2);
	printURL = 'siteForm/blankSiteForm.php?siteID=' + collectedData.siteID + '&stateFIPS=' + collectedData.stateFIPS + '&country=' + collectedData.countryCode + '&latDMS=' + latDMS[0] + '&latDecimal=' + latDMS[1] + '&lngDMS=' + lngDMS[0] + '&lngDecimal=' + lngDMS[1] + '&altitude=' + parseInt(collectedData.altitude) + '&altitudeDecimal=' + altDec + '&HUCCode=' + collectedData.HUC + '&countyCode=' + countyCode;
	currStationName = $('#SuggestedNames').find(":selected").text();
	$("#printThis").html('<iframe src="' + printURL + '&stationName=' + currStationName + '" style="display:none;" name="frame" id="theIframe"></iframe>');
	console.log(printURL + '&stationName=' + currStationName);
	//now insert data into print section

	//$("#printThis").html('<iframe src="../siteForm/blankSiteForm.php?stationName=" style="display:none;" name="frame" id="theIframe"></iframe>')

	// $("#siteIDPrint").text(collectedData.siteID);
	// $("#altitudePrint").text(collectedData.altitude);
	// $("#countryCodePrint").text(collectedData.countryCode);
	// $("#timezonePrint").text(collectedData.timeZoneCode);
	// $("#drainageAreaPrint").text(collectedData.contrDrainageArea);
	// $("#HUCPrint").text(collectedData.HUC);
	// $("#HUCNamePrint").text(collectedData.HUCName);
	// $("#statePrint").text(collectedData.state);
	// $("#countyPrint").text(collectedData.county);
	// $("#stateFIPSPrint").text(collectedData.stateFIPS);
	// $("#countyFIPSPrint").text(collectedData.countyFIPS);

}

//ajax functions

function ajaxSiteName () {
	on();
	return $.ajax({
		type : 'post',
		url: "../php/siteName.php",
		dataType: 'json',
		data:
        {
				'placeName' : collectedData.placeName,
				'placeNameState' : collectedData.placeNameState,
				'distanceNumber' : collectedData.distanceNumber,
				'GNIS_NAME' : collectedData.GNIS_NAME,
				'mouthOrOutlet' : collectedData.mouthOrOutlet,
				'cardinalDir' : collectedData.cardinalDir
        },
		success: function(theResult){
			counter += 25;
			console.log("Site name", counter);
			collectedData.suggSiteNames = JSON.parse(theResult);
		}});
}

function ajaxSiteID () {

	on();
	return $.ajax({
		type : 'post',
		url: "../php/siteID.php",
		dataType: 'json',
		data:
        {
				'lat' : collectedData.coords.lat,
				'lng' : collectedData.coords.lng
        },
		success: function(theResult1){
			var siteIDJSON = JSON.parse(theResult1);
			if (siteIDJSON && siteIDJSON.Results.length > 0) {
				collectedData.siteID = siteIDJSON.Results;
			} else {
				collectedData.siteID = "Needs revision.";
			}
			counter += 45;
			console.log("Site ID", counter);
		}});
}


function ajaxHUCInfo (e) {
	on();
	return $.ajax({
		url: "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/6/query?where=1%3D1&text=&objectIds=&time=&geometry=" + e.latlng.lng + "%2C" + e.latlng.lat + "&geometryType=esriGeometryPoint&inSR=4269&spatialRel=esriSpatialRelWithin&relationParam=&outFields=HUC12%2CNAME&returnGeometry=false&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&having=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&historicMoment=&returnDistinctValues=false&resultOffset=&resultRecordCount=&queryByDistance=&returnExtentOnly=false&datumTransformation=&parameterValues=&rangeValues=&quantizationParameters=&f=pjson",
		dataType: 'json',
		success: function(result){
			counter += 5;
			console.log("HUC Info", counter);
			collectedData.HUC = result.features[0].attributes.HUC12;
			collectedData.HUCName = result.features[0].attributes.NAME;
		}});
}

function ajaxContrDrainageArea (e) {
	// on();
	// return $.ajax({
	// 	url: "https://streamstats.usgs.gov/streamstatsservices/watershed.geojson?rcode=NY&xlocation=" + e.latlng.lng + "&ylocation=" + e.latlng.lat + "&crs=4326&includeparameters=false&includeflowtypes=false&includefeatures=true&simplify=true",
	// 	dataType: 'json',
	// 	success: function(result1){
	// 		if (result1.featurecollection[1] && result1.featurecollection[1].feature.features[0]) {
	// 			collectedData.contrDrainageArea = result1.featurecollection[1].feature.features[0].properties.Shape_Area;
	// 			collectedData.contrDrainageArea *= 10.764;
	// 		}
	// 		counter += 30;
	// }});
}

function ajaxTimeZoneCode (e) {
	on();
	return $.ajax({
		url: "https://api.timezonedb.com/v2.1/get-time-zone?key=FOG5KOCJ8U4T&format=json&by=position&lat=" + e.latlng.lat + "&lng=" + e.latlng.lng,
		dataType: 'json',
		success: function(result2){
			collectedData.timeZoneCode = result2.abbreviation;
			counter += 1;
			console.log("Time Zone", counter);
		}
	});
}

function ajaxAltitude (e) {
 	on();
	return $.ajax({
		url: "https://nationalmap.gov/epqs/pqs.php?x=" + e.latlng.lng + "&y=" + e.latlng.lat + "&units=Feet&output=json",
		dataType: 'json',
		success: function(result3){
			collectedData.altitude = result3.USGS_Elevation_Point_Query_Service.Elevation_Query.Elevation;
			counter += 2;
			console.log("Altitude", counter);
		}
	});
}

function ajaxCountryCode (e) {
	on();
	return $.ajax({
		url: "https://nominatim.openstreetmap.org/reverse?format=json&lat=" + e.latlng.lat + "&lon=" +  e.latlng.lng + "&zoom=18&addressdetails=1",
		dataType: 'json',
		success: function(result4){
			collectedData.countryCode = (result4.address.country_code).toUpperCase();
			counter += 1;
			console.log("Country code", counter);
		},
		error: function(XMLHttpRequest, textStatus, errorThrown) {
			if (confirm("Network error. Try again?")) {
				counter = 0;
				callAjaxCalls(e);
			}
		},
		timeout: 10000 // sets timeout to 10 seconds
	});
}

function ajaxCountyStateFIPS (e) {
	on();
	return $.ajax({
		url: "https://geo.fcc.gov/api/census/block/find?latitude=" + e.latlng.lat + "&longitude=" + e.latlng.lng + "&showall=false&format=json",
		dataType: 'json',
		success: function(result5){
			counter += 1;
			console.log("County/State", counter);
			collectedData.county = result5.County.name;
			collectedData.state = result5.State.name;
			collectedData.stateCode = result5.State.code;

			collectedData.stateFIPS = result5.State.FIPS;
			collectedData.countyFIPS = result5.County.FIPS;
		}
	});
}
//getLayerId
function ajaxSiteLocs (callback) {
	//on();

	var bounds = map.getBounds();
	var nwBound = bounds.getNorthWest();
	var seBound = bounds.getSouthEast();
	
	//https://waterdata.usgs.gov/nwis/inventory?nw_longitude_va=-77.459070&nw_latitude_va=42.970432&se_longitude_va=-77.559070&se_latitude_va=42.870432&coordinate_format=decimal_degrees&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=dec_lat_va&column_name=dec_long_va&list_of_search_criteria=lat_long_bounding_box
	//https://waterdata.usgs.gov/nwis/inventory?nw_longitude_va=-77.459070&nw_latitude_va=42.970432&se_longitude_va=-77.316980&se_latitude_va=41.572236&coordinate_format=decimal_degrees&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=site_tp_cd&column_name=dec_lat_va&column_name=dec_long_va&list_of_search_criteria=lat_long_bounding_box
	$.ajax({
		url: "https://waterdata.usgs.gov/nwis/inventory?nw_longitude_va=" + nwBound.lng + "&nw_latitude_va=" + nwBound.lat + "&se_longitude_va=" + seBound.lng + "&se_latitude_va=" + seBound.lat + 
		"&coordinate_format=decimal_degrees&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=site_tp_cd&column_name=dec_lat_va&column_name=dec_long_va&list_of_search_criteria=lat_long_bounding_box",
		dataType: 'xml',
		success: function(xml){
			console.log("success");
			callback(xml);
		}
	});
}

function updateMapSitesCallback (xml) {
	preexistingSiteLayer.clearLayers();
	var myRenderer = L.canvas({ padding: 0.5 });
	myRenderer.addTo(preexistingSiteLayer);
	$(xml).find('site').each(function(){
		var type = $(this).find("site_tp_cd").text();
		var streamCode = "ST";
		if(type.localeCompare(streamCode) == 0) {
			var lat = $(this).find("dec_lat_va").text();
			var lng = $(this).find("dec_long_va").text();
			var name = $(this).find("station_nm").text();
			var siteID = $(this).find("site_no").text();

			var tooltip = name.length > 0 ? name + "\nID: " + siteID : siteID;
		
			L.marker(L.latLng(lat, lng), {title: tooltip}).addTo(preexistingSiteLayer);
		}
	});
}

function verifyMapSiteSnapsCallback (xml) {
	updateMapSitesCallback(xml);
}
 
/*
$.when(ajaxHUCInfo(e), ajaxContrDrainageArea(e), ajaxTimeZoneCode(e), ajaxAltitude(e), ajaxCountryCode(e), ajaxCountyStateFIPS(e), ajaxNearbyPlace(e)).done(function(a1, a2, a3, a4, a5, a6, a7){
		$.when(ajaxSiteName(), ajaxSiteID()).done(function(a8, a9){
			//showFoundData();
		});
	});
*/

//attempt to get streams in a radius around latlng. Send features to callback in format callback(results)
function ajaxGetStreams (latlng, callback) {
	var radius = 2000;
	var queryUrl = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6/query?geometry=" + latlng.lng + "," + latlng.lat + "&outFields=GNIS_NAME%2CREACHCODE&geometryType=esriGeometryPoint&inSR=4326&outSR=4326&distance=" + radius + "&units=esriSRUnit_Meter&outFields=*&returnGeometry=true&f=pjson";
	
	if (queryingStreams == true) {
		console.log("already querying");
		return;
	}
	
	queryingStreams = true;

	

	return $.ajax({
		url: queryUrl,
		dataType: 'json',
		timeout: 5000,
		success: function(results){
			queryingStreams = false;
			currentQueriedStreams = [results.features, latlng, radius]
			callback(latlng, results.features);
		},
		error: function(){
			queryingStreams = false;
			console.log("query failure. Attempting again.");
		},
	});
}

function snapToFeature (latlng, features) {
	var smallestDistFeature = Number.MAX_VALUE;
	var smallestDistFeatureIndex = -1;
	var feature = null;
	for (var feat of features) {
		var smallestDist = "";
		var smallestDistIndex;
		for (var i = 0; i < feat.geometry.paths[0].length; i++) {
			var dist = distance(latlng.lat, latlng.lng, feat.geometry.paths[0][i][1], feat.geometry.paths[0][i][0]);
			if(dist < smallestDistFeature){
				smallestDistFeature = dist;
				smallestDistFeatureIndex = i;
				feature = feat
			}
		}
	}

	if(smallestDistFeatureIndex == -1){
		console.error("found no nearest feature returning [-1, -1]");
		return [-1, -1];
	}

	//find nearest coordinate
	globSmallestDistIndex = smallestDistFeatureIndex;

	//now find whether left or right of smallestDistIndex is closer

	var leftDist = Number.MAX_VALUE;
	var rightDist = Number.MAX_VALUE;
	//left
	if (smallestDistFeatureIndex != 0) {
		leftDist = distance(latlng.lat, latlng.lng, feature.geometry.paths[0][smallestDistFeatureIndex - 1][1], feature.geometry.paths[0][smallestDistFeatureIndex - 1][0]);
	}

	if (smallestDistFeatureIndex != feature.geometry.paths[0].length - 1) {
		rightDist = distance(latlng.lat, latlng.lng, feature.geometry.paths[0][smallestDistFeatureIndex + 1][1], feature.geometry.paths[0][smallestDistFeatureIndex + 1][0]);
	}
	var leftCoordOfLine;
	var rightCoordOfLine;
	if (leftDist < rightDist) {
		leftCoordOfLine = feature.geometry.paths[0][smallestDistFeatureIndex - 1];
		rightCoordOfLine = feature.geometry.paths[0][smallestDistFeatureIndex];
	} else {
		leftCoordOfLine = feature.geometry.paths[0][smallestDistFeatureIndex];
		rightCoordOfLine = feature.geometry.paths[0][smallestDistFeatureIndex + 1];
	}

	//now calculate closest "nonreal" point on line
	var A = {
		x : leftCoordOfLine[1],
		y : leftCoordOfLine[0]
	};

	var B = {
		x : rightCoordOfLine[1],
		y : rightCoordOfLine[0]
	};

	var C = {
		x : latlng.lat,
		y : latlng.lng
	};

	var D = getSpPoint(A,B,C);

	//check if the projected point is in the line segment

	var isInLineSegm = calcIsInsideLineSegment(A,B,D);

	if (!isInLineSegm) {
		D.x = feature.geometry.paths[0][smallestDistFeatureIndex][1];
		D.y = feature.geometry.paths[0][smallestDistFeatureIndex][0];
	}

	return [D.x, D.y];
}

function getSnappedPointThenRun (latlng) {

	if (currentQueriedStreams != null) {
		currentQueryFeatures = currentQueriedStreams[0]
		currentQueryCenter = currentQueriedStreams[1]
		currentQueryRad = currentQueriedStreams[2]

		if (latlng.distanceTo(currentQueryCenter) < currentQueryRad/2)
		{
			console.log("within previous");
			getSnappedPointThenRunCallback(latlng, currentQueryFeatures);
		}
	} 

	ajaxGetStreams(latlng, getSnappedPointThenRunCallback);
}

function getSnappedPointThenRunCallback (latlng, features) {
	var snappedLatlng = snapToFeature(latlng, features);
	highlightFeature(features);
	marker.setLatLng(snappedLatlng);

	map.flyTo(marker.getLatLng(), 14)

	var popup = L.popup({offset: L.point(0,-50)})
	.setLatLng(snappedLatlng)
	.setContent('<p>Is this location correct?</p><button type="button" class="btn" id="notCorr">No</button><button type="button" class="btn btn-primary" id="yesCorr" style = "float:right;">Yes</button>')
	.openOn(map);
	$("#notCorr").click(function(){
		map.closePopup();
	});
	$("#yesCorr").click(function(){
		map.closePopup();
		collectedData.coords = snappedLatlng;
		collectedData.coords.x = snappedLatlng.lat;
		collectedData.coords.y = snappedLatlng.lng;
		//globFeature = feature;
		callAjaxCalls(e);
	}); 
}

function highlightFeature (features) {
	highlightedStreamsLayer.clearLayers();
	for (var feature of features) {
		var points = [];
		for (const point of feature.geometry.paths[0]) {
			points.push(new L.LatLng(point[1], point[0]));
		}
		firstpolyline = new L.Polyline(points, {
			color: 'red',
			weight: 3,
			opacity: 0.5,
			smoothFactor: 1
		});
		firstpolyline.addTo(highlightedStreamsLayer);
	}
}


function ajaxNearbyPlace (e) {
	on();
	var feature = null;//globFeature;
	collectedData.GNIS_NAME = feature.attributes.GNIS_NAME;
	collectedData.REACHCODE = feature.attributes.REACHCODE;

	//find if near mouth or outlet
	var calcDist = .05 * feature.geometry.paths[0].length;
	if (calcDist < 1) {
		calcDist = 1;
	}
	calcDist = Math.round(calcDist);
	if (globSmallestDistIndex <= calcDist) {
		collectedData.mouthOrOutlet = "mouth";
	} else if (globSmallestDistIndex >= feature.geometry.paths[0].length - 1 - calcDist) {
		collectedData.mouthOrOutlet = "outlet";
	}

	return $.ajax({
		url: "https://carto.nationalmap.gov/arcgis/rest/services/geonames/MapServer/18/query?geometry=" + collectedData.coords.y +"," + collectedData.coords.x + "&geometryType=esriGeometryPoint&inSR=4326&outSR=4326&distance=7000&units=esriSRUnit_Meter&outFields=*&returnGeometry=true&f=pjson",
		dataType: 'json',
		success: function(result7){
			console.log('RESULT',result7)
			counter += 20;
			console.log("Nearby", counter);
			//see if found any
			var theFeatures = result7.features;
			var howMany = theFeatures.length;
			if (howMany > 0) {
				var closestDist = Number.MAX_VALUE;
				var closestFeature = undefined;
				var closestCoords = undefined;
				for (var feature of theFeatures) {
					var theCoords = feature.geometry.points[0];
					var currDist = distance(collectedData.coords.y, collectedData.coords.x, theCoords[0], theCoords[1]) / 1.609344;
					if (currDist < closestDist) {
						closestDist = currDist;
						closestFeature = feature;
						closestCoords = theCoords;
					}
				}

				collectedData.placeName = closestFeature.attributes.gaz_name;
				console.log("FOUND CLOSEST POPULATED PLACE:", collectedData.placeName);

				var distMiles = closestDist;

				collectedData.distanceNumber = distMiles;
				collectedData.placeNameState = closestFeature.attributes.state_alpha;

				var n = getHorizontalBearing(closestCoords[0], closestCoords[1], collectedData.coords.y, collectedData.coords.x);
				console.log("horizontal bearing: " + n);

				//find cardinal direction from bearing

				if (n < 112.5 && n >= 67.5) {
					collectedData.cardinalDir = "north";
				} else if (n < 67.5 && n >= 22.5) {
					collectedData.cardinalDir = "north east";
				} else if (n < 22.5 || n >= 337.5) {
					collectedData.cardinalDir = "east";
				} else if (n < 337.5 && n >= 292.5) {
					collectedData.cardinalDir = "south east";
				} else if (n < 292.5 && n >= 247.5) {
					collectedData.cardinalDir = "south";
				} else if (n < 247.5 && n >= 202.5) {
					collectedData.cardinalDir = "south west";
				} else if (n < 202.5 && n >= 157.5) {
					collectedData.cardinalDir = "west";
				} else {
					collectedData.cardinalDir = "north west";
				}
			}
		},
		error: function(XMLHttpRequest, textStatus, errorThrown) {
			if (confirm("Network error. Try again?")) {
				counter = 0;
				callAjaxCalls(e);
			}
		},
		timeout: 10000 // sets timeout to 10 seconds
	});
}


//main document ready function
$(document).ready(function () {

	// document.getElementById("btnPrint").onclick = function () {
	// 	var chosenSiteName = $('#SuggestedNames').find(":selected").text();
	// 	$("#siteNamePrint").text(chosenSiteName);
	// 	printElement(document.getElementById("printThis"));
	// }

	//initialize basemap
	var worldImagery = L.tileLayer("https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}", {
		attribution: 'Copyright: &copy; 2013 Esri, DeLorme, NAVTEQ'
	});
	var worldBoundAndPlacesRef = L.tileLayer("https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
		attribution: 'Copyright: &copy; 2013 Esri, DeLorme, NAVTEQ'
	});

	//initialize map
	map = new L.Map('map', {
		center: new L.LatLng(42.75, -75.5),
		zoom: 7,
		layers: [worldImagery, worldBoundAndPlacesRef],
		attributionControl: false,
		zoomControl: false
	});

	//set up a layer group that will hold the preexisting sites
	preexistingSiteLayer = L.layerGroup();
	preexistingSiteLayer.addTo(map);

	highlightedStreamsLayer = L.layerGroup();
	highlightedStreamsLayer.addTo(map);

	map.on('moveend', function (e) {
		if(map.getZoom() >= 13) {
			siteLocRenderer = ajaxSiteLocs(updateMapSitesCallback);
		}
		else {
			preexistingSiteLayer.clearLayers();
		}
	});

	marker = new L.Marker([0,0], { draggable: true}).addTo(map);
	var popup = L.popup({offset: L.point(0,-50)})
	//.setLatLng([42.75, -75.5])
	.setContent('<p>Choose this location?</p><button type="button" class="btn" id="noLoc">No</button><button type="button" class="btn btn-primary" id="yesLoc" style = "float:right;">Yes</button>');


	marker.on('dragend', function(ev) {
		moveMarker(marker, marker.getLatLng());
		confirmLoc(marker, popup);
	});

	map.on('click', function(e) {
		var latlng = map.mouseEventToLatLng(e.originalEvent);

		moveMarker(marker, latlng);
		confirmLoc(marker, popup);
	});

	$("#coordsSubmit").click(function(){

		var lat = $('#latitude').val();
		var lng = $('#longitude').val();

		//make sure both fields are filled out
		if (lati == "" || longi == "") {
			alert("You must fill in both fields!");
		} else {
			$('#coordModal').modal('hide');
			map.closePopup();

			moveMarker(marker, [lat, lng]);
			confirmLoc(marker, popup);
		}
		return false;
	});

	function confirmLoc (marker, popup) {
		var latlng = marker.getLatLng();
		if(popup.isPopupOpen()) {
			popup.setLatLng(latlng);
		}
		else {
			popup.setLatLng(latlng);
			popup.openOn(map);
		 }

		$("#yesLoc").click(function(){
			console.log("yes");
			popup.closePopup();
			var latlng = marker.getLatLng();
			var e = {
				latlng : {
					lat: latlng.lat,
					lng: latlng.lng
				},
			};
			console.log(latlng);
			var markerLoc = marker.getLatLng();
			var bounds = getBoundingBox([markerLoc.lat, markerLoc.lng], 30);
			//map.fitBounds(bounds);
			
			getSnappedPointThenRun(latlng);
		});
		$("#noLoc").click(function(){
			map.closePopup();
		});
	}

	function moveMarker (marker, newLocation) {
		$("#SuggestedNames").html("");
		$("#SiteID").val("");
		$("#Alt").val("");
		$("#CC").val("");
		$("#TimeZone").val("");
		$("#Drain").val("");
		$("#HUC").val("");
		$("#HUCN").val("");
		$("#State").val("");
		$("#County").val("");
		$("#StateFIPS").val("");
		$("#CountyFIPS").val("");

		//now clear data in print section

		$("#siteIDPrint").text("");
		$("#altitudePrint").text("");
		$("#countryCodePrint").text("");
		$("#timezonePrint").text("");
		$("#drainageAreaPrint").text("");
		$("#HUCPrint").text("");
		$("#HUCNamePrint").text("");
		$("#statePrint").text("");
		$("#countyPrint").text("");
		$("#stateFIPSPrint").text("");
		$("#countyFIPSPrint").text("");
		$("#siteNamePrint").text("");

		marker.setLatLng(newLocation);
	}
	//end document ready function
});
