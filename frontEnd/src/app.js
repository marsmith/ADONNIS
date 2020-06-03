// ------------------------------------------------------------------------------
// ----- ADONNIS -----------------------------------------------------------------
// ------------------------------------------------------------------------------

// copyright:   2018 Martyn Smith - USGS NY WSC

// authors:   Martyn J. Smith - USGS NY WSC
//            Ian G. Scilipoti - USGS NY WSC

// purpose:  USGS NY WSC Web App Template

// updates:
// 08.07.2018 - MJS - Created
// 04.24.2020 - MJS - Updates/modularized
// 05.19.2020 - IGS - added ADONNIS features

//CSS imports
import 'bootstrap/dist/css/bootstrap.css';
import 'marker-creator/app/stylesheets/css/markers.css';
import 'leaflet/dist/leaflet.css';
import './styles/main.css';

//ES6 imports
import 'bootstrap/js/dist/util';
import 'bootstrap/js/dist/modal';
import 'bootstrap/js/dist/collapse';
import 'bootstrap/js/dist/tab';
import { map, control, featureGroup, Icon } from 'leaflet';
import { basemapLayer } from 'esri-leaflet';
import { library, dom } from '@fortawesome/fontawesome-svg-core';
import { faBars } from '@fortawesome/free-solid-svg-icons/faBars';
import { faInfo } from '@fortawesome/free-solid-svg-icons/faInfo';
import { faPlus } from '@fortawesome/free-solid-svg-icons/faPlus';
import { faMinus } from '@fortawesome/free-solid-svg-icons/faMinus';
import { faExclamationCircle } from '@fortawesome/free-solid-svg-icons/faExclamationCircle';
import { faQuestionCircle } from '@fortawesome/free-solid-svg-icons/faQuestionCircle';
import { faCog } from '@fortawesome/free-solid-svg-icons/faCog';
import { faTwitterSquare } from '@fortawesome/free-brands-svg-icons/faTwitterSquare';
import { faFacebookSquare } from '@fortawesome/free-brands-svg-icons/faFacebookSquare';
import { faGooglePlusSquare } from '@fortawesome/free-brands-svg-icons/faGooglePlusSquare';
import { faGithubSquare } from '@fortawesome/free-brands-svg-icons/faGithubSquare';
import { faFlickr } from '@fortawesome/free-brands-svg-icons/faFlickr';
import { faYoutubeSquare } from '@fortawesome/free-brands-svg-icons/faYoutubeSquare';
import { faInstagram } from '@fortawesome/free-brands-svg-icons/faInstagram';

library.add(faBars, faPlus, faMinus, faInfo, faExclamationCircle, faCog, faQuestionCircle, faTwitterSquare, faFacebookSquare,faGooglePlusSquare, faGithubSquare, faFlickr, faYoutubeSquare, faInstagram );
dom.watch();

//START user config variables
var MapX = '-74.58'; //set initial map longitude
var MapY = '41.905'; //set initial map latitude
var MapZoom = 8; //set initial map zoom
var NWISsiteServiceURL = 'https://waterservices.usgs.gov/nwis/site/';
var NHDserviceURL = 'https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6/query/';
var NHDserviceURLalt = 'https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/2/query';
var supportEmail = "iscilipoti@contractor.usgs.gov";
var streamLevelColors = ["#ff2f00", "#ff00d4", "#1500ff", "#00fff7", "#04ff00", "#d4ff00", "#ffd000", "#ff5900", "#ff8282", "#949494"]

var NHDstreamRadius = 2000;
var siteDisplayZoomLevel = 12;
var siteHighlightZoomLevel = 15;
//END user config variables 

//START global variables
var theMap;
var baseMapLayer, basemaplayerLabels;

var nwisSitesLayer;//leaflet layer that displays NWIS sites
var NWISmarkers;//list of all NWIS markers on the map currently
var queriedNetworkLayer;//layer that displays lines queried on backend
var highlightedLocationsLayer;

var NHDlinesLayer;
var isQueryingLines;
var lastQueriedFeatures;
var lastQueryLatlng;

var cursor;
var cursorIcon;
var siteIcon;
var snappedCursorLatLng;
var currentResultsIDs = []; //these are the ID(s) that are displayed as results. Keep track so we can hyperlink them properly
var currentResultsLatLng;

var idNumLinkClass = "idNum"
//END global variables

//instantiate map
$(document).ready(function () {

  console.log('Application Information: ' + process.env.NODE_ENV + ' ' + 'version ' + VERSION);
  $('#appVersion').html('Application Information: ' + process.env.NODE_ENV + ' ' + 'version ' + VERSION);

  initializeMap();
  initListeners();

});

function initializeMap() {
  Icon.Default.imagePath = './images/';

  //create map
  theMap = map('mapDiv', { zoomControl: false, minZoom: 8, preferCanvas: true});

  //add zoom control with your options
  control.zoom({ position: 'topright' }).addTo(theMap);
  control.scale().addTo(theMap);

  //basemap
  baseMapLayer = basemapLayer('ImageryClarity').addTo(theMap);;

  //set initial view
  theMap.setView([MapY, MapX], MapZoom);

  //define layers
  nwisSitesLayer = featureGroup().addTo(theMap);
  queriedNetworkLayer = featureGroup().addTo(theMap);
  NHDlinesLayer = featureGroup().addTo(theMap);
  highlightedLocationsLayer = featureGroup().addTo(theMap);

  //hide laoding spinner
  $('#loading').hide();
  $('#highPriorityWarnings').hide();
  $('#mediumPriorityWarnings').hide();
  $('#adonnisResults').hide();
  $('#frontEndFailure').hide();

  cursorIcon = L.divIcon({className: 'wmm-pin wmm-yellow wmm-icon-diamond wmm-icon-blue wmm-size-25'});
  siteIcon = L.divIcon({className: 'wmm-pin wmm-altblue wmm-icon-diamond wmm-icon-blue wmm-size-25'});
  NWISmarkers = {};
}

function initListeners() {

  /*  START EVENT HANDLERS */
  theMap.on('zoomend dragend', function() {

    //only query if zoom is reasonable
    if (theMap.getZoom() >= siteDisplayZoomLevel) {
      queryNWISsites(theMap.getBounds());
    }
  });

  theMap.on('click', function(e) {
		var latlng = theMap.mouseEventToLatLng(e.originalEvent);

		moveCursor(latlng);
	});

  var lastZoom;
  var tooltipThreshold = 13;
  theMap.on('zoomend', function() {
      var zoom = theMap.getZoom();
      if (zoom < tooltipThreshold && (!lastZoom || lastZoom >= tooltipThreshold)) {
        theMap.eachLayer(function(l) {
              if (l.getTooltip()) {
                  var tooltip = l.getTooltip();
                  l.unbindTooltip().bindTooltip(tooltip, {
                      permanent: false
                  })
              }
          })
      } else if (zoom >= tooltipThreshold && (!lastZoom || lastZoom < tooltipThreshold)) {
        theMap.eachLayer(function(l) {
              if (l.getTooltip()) {
                  var tooltip = l.getTooltip();
                  l.unbindTooltip().bindTooltip(tooltip, {
                      permanent: true
                  })
              }
          });
      }
      if (theMap.getZoom() < siteDisplayZoomLevel) {
        nwisSitesLayer.clearLayers();
      }
      lastZoom = zoom;
  })


  $('.basemapBtn').click(function () {
    $('.basemapBtn').removeClass('slick-btn-selection');
    $(this).addClass('slick-btn-selection');
    var baseMap = this.id.replace('btn', '');
    setBasemap(baseMap);
  });

  $('#mobile-main-menu').click(function () {
    $('body').toggleClass('isOpenMenu');
  });

  $('#aboutButton').click(function () {
    alert('clicked');
    $('#aboutModal').modal('show');
  });

  nwisSitesLayer.on('click', function (e) {
    
  });
  
  $("#enterLatLng").click(function(){
    var lat = $('#latitude').val();
    var lng = $('#longitude').val();

    var latf = parseFloat(lat);
    var lngf = parseFloat(lng);
    if (latf != NaN && lngf != NaN){
      var latlng = L.latLng(latf, lngf);
      moveCursor(latlng);
    }
  });

  $("#adonnisResults").on("click", "[class='" + idNumLinkClass + "']", function(event){
    var siteID = $( this ).text();
    goToSite(siteID);
  });

  $("#adonnisResults").on("mouseover", "[class='" + idNumLinkClass + "']", function(event){
    var siteID = $( this ).text();
    highlightSite(siteID);
  });

  $("#adonnisResults").on("mouseleave", "[class='" + idNumLinkClass + "']", function(event){
    highlightedLocationsLayer.clearLayers();
  });

  /*  END EVENT HANDLERS */

  $('.leaflet-container').css('cursor','crosshair');
}

function moveCursor (latlng, snap = true) {
  
  $('#adonnisResults').hide();
  $('#latitude').val(latlng.lat);
  $('#longitude').val(latlng.lng);
  
  if(lastQueriedFeatures != null && latlng.distanceTo(lastQueryLatlng) < NHDstreamRadius/2 || snap == false) {
    var snappedLatLng = latlng;
    if (snap == true) {
      snappedLatLng = snapToFeature(latlng, lastQueriedFeatures);
    }
    
    if (cursor == null) {
      cursor = L.marker(snappedLatLng, {icon: cursorIcon}).addTo(theMap);
      cursor.bindPopup('<p>Is this location correct?</p><button type="button" class="btn" id="notCorr">No</button><button type="button" class="btn btn-primary" id="yesCorr" style = "float:right;">Yes</button>', {offset: L.point(0,-20)});      
    }
    else {
      cursor.setLatLng(snappedLatLng);
    }
    moveAttentionToCursor();
    cursor.openPopup();
    snappedCursorLatLng = snappedLatLng;

    $("#notCorr").click(function(){
      cursor.closePopup();
    });
    $("#yesCorr").click(function(){
      cursor.closePopup();
      querySiteInfo(snappedCursorLatLng, displaySiteInfo);
      $('body').toggleClass('isOpenMenu');
    });
  }
  else {
    queryNHDStreams (latlng, function(){ moveCursor(latlng)}, null, function() { moveCursor(latlng, false);});
  }
}

function displaySiteInfo (siteInfo, latLng)
{
  $('#adonnisResults').show();
  $('#initialAdvice').hide();

  var names = siteInfo["names"];
  var namesHTML = ""
  for (var name of names){
    
    namesHTML += getAlertHTML(name, "secondary");
  }

  $('#namesDisp').html(namesHTML);
  
  var log = siteInfo["log"];

  var numLowPriority = log["lowPriority"].length;
  var numMediumPriority = log["mediumPriority"].length;
  var numHighPriority = log["highPriority"].length;
  var totalWarnings = numLowPriority + numMediumPriority + numHighPriority;

  var siteIDalertType = numHighPriority > 0 ? 'danger' : (numMediumPriority > 0 ? 'warning' : 'success');

  var idInfo = siteInfo["idInfo"];
  var idInfoAlt = siteInfo["idInfoAlt"];

  currentResultsIDs = [];
  currentResultsIDs.push(stripIDHTMLFormat(idInfo["id"]));
  currentResultsLatLng = latLng;

  $('#siteIdDisp').html(getAlertHTML(fillIDHTML(idInfo["id"]), siteIDalertType));
  $('#storyDisp').html(fillIDHTML(idInfo["story"]));
  
  if (idInfoAlt != null){
    currentResultsIDs.push(stripIDHTMLFormat(idInfoAlt["id"]));
    $('#alternateResults').show();
    //fill warning automatically since we only get alt results given 3rd tier warning
    //3rd tier warnings always come with 2nd tier warnings..
    $('#siteIdDispAlt').html(getAlertHTML(fillIDHTML(idInfoAlt["id"]), 'warning'));
    $('#storyDispAlt').html(fillIDHTML(idInfoAlt["story"]));
  }
  else {
    $('#alternateResults').hide();
  }
  

  if (totalWarnings > 0) {
    $('#warningSection').show();
    //display warning banners
    if (numMediumPriority > 0) {
      $('#mediumPriorityWarnings').show();
    }

    if (numHighPriority > 0) {
      $('#highPriorityWarnings').show();
    }

    var warningsHTML = "";

    for (var warning of log["highPriority"]) {
      warningsHTML += getAlertHTML(fillIDHTML(warning["body"]), "danger")
    }

    for (var warning of log["mediumPriority"]) {
      warningsHTML += getAlertHTML(fillIDHTML(warning["body"]), "warning");
    }

    for (var warning of log["lowPriority"]) {
      warningsHTML += getAlertHTML(fillIDHTML(warning["body"]), "info");
    }

    $('#warningsDisp').html(warningsHTML);
  }
  else {
    $('#warningSection').hide();
  }
  if (queriedNetworkLayer != null) {
    queriedNetworkLayer.clearLayers();
  }

  if ("network" in siteInfo) {
    var network = siteInfo["network"]
    queriedNetworkLayer = L.geoJSON(network, {
      style: function(feature) {
        var level = parseInt(feature.properties.streamLevel)
        return {color: streamLevelColors[level]};
      }
    }).addTo(queriedNetworkLayer);
    NHDlinesLayer.clearLayers();
  }
}

function querySiteInfo (latLng, callback) {
  $('#frontEndFailure').hide();
  //callback({"idInfo": {"id": "_01362013_", "story": "Requested site info at 42.273, -73.959. ADONNIS used sites with incorrect ID's when calculating the new ID. Found a upstream site _01362032_ and a downstream site _0136200705_. New site is the weighted average of these two sites."}, "idInfoAlt": {"id": "_0136202825_", "story": "Requested site info at 42.273, -73.959. ADONNIS ignored sites with incorrect ID's when calculating the new ID. Found an upstream site _01362028_. Based on list of all sites, assume that _01362030_ is the nearest sequential downstream site. New ID is based on the upstream site and bounded by the sequential downstream site"}, "log": {"lowPriority": ["Found upstream and downstream bound. But, downstream bound is based on list of sequential sites and may not be the true downstream bound. This could result in site ID clustering."], "mediumPriority": ["_0136200705_ conflicts with 7 other sites. Consider changing this site's ID", "_01362005_ conflicts with 6 other sites. Consider changing this site's ID", "_01362008_ conflicts with _01362004_. Consider changing the site ID of one of these two sites", "_01362032_ conflicts with _01362030_. Consider changing the site ID of one of these two sites", "_0136200705_ conflicts with 7 other sites. Consider changing this site's ID", "_01362005_ conflicts with 6 other sites. Consider changing this site's ID", "_01362015_ conflicts with 5 other sites. Consider changing this site's ID", "_01362008_ conflicts with _01362004_. Consider changing the site ID of one of these two sites", "_01362032_ conflicts with _01362030_. Consider changing the site ID of one of these two sites"], "highPriority": ["_01362032_ was used to generate results AND is involved in a site conflict. See story/medium priority warnings for conflict details.", "_0136200705_ was used to generate results AND is involved in a site conflict. See story/medium priority warnings for conflict details.", "The found upstream site is larger than found downstream site. ADONNIS output almost certainly incorrect."]}, "names": ["BELL BROOK TRIBUTARY AT SOUTH CAIRO NY", "BELL BROOK TRIBUTARY AT MOUTH AT SOUTH CAIRO NY", "BELL BROOK TRIBUTARY NEAR BELL BROOK AT SOUTH CAIRO NY", "BELL BROOK TRIBUTARY AT MOUTH NEAR BELL BROOK AT SOUTH CAIRO NY", "BELL BROOK TRIBUTARY 0.4 MILES WEST OF BELL BROOK AT SOUTH CAIRO NY", "BELL BROOK TRIBUTARY AT MOUTH 0.4 MILES WEST OF BELL BROOK AT SOUTH CAIRO NY"]}, latLng);
  //return;
  $('#loading').show();
  console.log("attemping site info query");
	return $.ajax({ 
		type : 'post',
		url: "./siteID.php",
		dataType: 'json',
		data:
        {
				'lat' : latLng.lat,
				'lng' : latLng.lng
        },
		success: function(theResult){
      var resultsJSON = JSON.parse(theResult);
      console.log("result is: " + theResult);
			if (resultsJSON) {
				callback(resultsJSON, latLng);
			} else {
				console.log("couldn't read results");
      }
      $('#loading').hide();
    },
    error: function(jqXH, text, errorThrown){
      console.log("failed query: " + text + " error=" + errorThrown);
      console.log(jqXH.responseText);
      $('#loading').hide(); 
      var emailBody = "A fatal issue occured at the coordinates: " + latLng.lat + ", " + latLng.lng + ".";
      var warningBody = 'Failure parsing results from backend. <a href="mailto:' + supportEmail + '?subject=ADONNIS failure&body=' + emailBody + '">Help improve ADONNIS by sharing the lat/long in question</a>.';
      showFrontendWarning(warningBody, 2);
    },
  }); 
}

//severity 1 is yellow warning. severity 2 is danger warning
function showFrontendWarning (body, severity) {
  var severityAlertTags = ["success", "warning", "danger"];
  $('#frontEndFailure').html(getAlertHTML(body, severityAlertTags[severity]));
  $('#frontEndFailure').show();
}

function getAlertHTML (body, alertTag) {
  
  var openTag = '<div class="alert alert-' + alertTag + '">';
  var closeTag = '</div>';
  return openTag + body + closeTag;
}

//attempt to get streams in a radius around latlng. Send features to callback in format callback(results)
function queryNHDStreams (latlng, callback, retryService, failureCallback) {
  
  console.log('querying NHD', NHDstreamRadius);
  //var queryUrl = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/2/query?geometry=" + latlng.lng + "," + latlng.lat + "&outFields=GNIS_NAME%2C+LENGTHKM%2C+STREAMLEVE%2C+FCODE%2C+OBJECTID%2C+ARBOLATESU&geometryType=esriGeometryPoint&inSR=4326&outSR=4326&distance=" + NHDstreamRadius + "&units=esriSRUnit_Meter&returnGeometry=true&f=pjson";
  var queryUrl = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6/query?geometry=" + latlng.lng + "," + latlng.lat + "&outFields=GNIS_NAME%2CREACHCODE&geometryType=esriGeometryPoint&inSR=4326&outSR=4326&distance=" + NHDstreamRadius + "&units=esriSRUnit_Meter&outFields=*&returnGeometry=true&f=pjson";
  //                https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6/?geometry=-74.60977282623656%2C41.841805710824715&geometryType=esriGeometryPoint&inSR=4326&outSR=4326&distance=3000&units=esriSRUnit_Meter&returnGeometry=true&f=pjson
	
	if (isQueryingLines == true) {
		console.log("already querying");
		return;
	}
  isQueryingLines = true;

  $('#loading').show();

  var args = {
    'geometry': latlng.lng + "," + latlng.lat,
    'geometryType':'esriGeometryPoint',
    'inSR':'4326',
    'outSR':'4326',
    'distance':NHDstreamRadius,
    'units':'esriSRUnit_Meter',
    'returnGeometry':'true',
    'f':'pjson'
  };
  var serviceURL = retryService ? retryService : NHDserviceURL;
	return $.ajax({
		url: serviceURL,
		dataType: 'json',
    timeout: 7000,
    data: args,
		success: function(results){
      console.log("query success")
      isQueryingLines = false;
      lastQueriedFeatures = results.features;
      lastQueryLatlng = latlng
      highlightFeature(lastQueriedFeatures);
      $('#loading').hide();
      $('#frontEndFailure').hide();
      callback()
		},
		error: function(jqXH, text, errorThrown){
      console.log("failed query: " + text + " error=" + errorThrown);
      console.log(jqXH.responseText);
      isQueryingLines = false;
      //if (retryService != null) {
      $('#loading').hide(); 
      showFrontendWarning("Could not connect to NHD server. Could not snap point to NHD data.", 1);
      if (failureCallback != null) {
        failureCallback();
      }
      //}
      //else {
      //  console.log("retrying alt URL");
      //  queryNHDStreams(latlng, callback, NHDserviceURL);
      //}
		},
	});
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

function moveAttentionToCursor ()
{
  if (theMap.getZoom() > 14) {
    theMap.panTo(cursor.getLatLng());
  }
  else {
    theMap.flyTo(cursor.getLatLng(), 14);
  }
}

function highlightFeature (features) {
	NHDlinesLayer.clearLayers();
	for (var feature of features) {
		var points = [];
		for (const point of feature.geometry.paths[0]) {
			points.push(new L.latLng(point[1], point[0]));
		}
		var firstpolyline = new L.Polyline(points, {color: 'blue', weight: 3, opacity: 0.5, smoothFactor: 1});
		firstpolyline.addTo(NHDlinesLayer);
	}
}

function snapToFeature (latlng, features) {
	var smallestDistFeature = Number.MAX_VALUE;
	var smallestDistFeatureIndex = -1;
	var feature = null;
	for (var feat of features) {
		var smallestDist = "";
		var smallestDistIndex;
		for (var i = 0; i < feat.geometry.paths[0].length; i++) {
      var geomPoint = L.latLng(feat.geometry.paths[0][i][1], feat.geometry.paths[0][i][0])
			var dist = geomPoint.distanceTo(latlng);
			if(dist < smallestDistFeature){
				smallestDistFeature = dist;
				smallestDistFeatureIndex = i;
				feature = feat
			}
		}
	}

	if(smallestDistFeatureIndex == -1){
		console.error("found no nearest feature returning unsnapped latlng");
		return latlng;
	}

	//now find whether left or right of smallestDistIndex is closer

	var leftDist = Number.MAX_VALUE;
	var rightDist = Number.MAX_VALUE;
	//left
	if (smallestDistFeatureIndex != 0) {
    var leftPoint = L.latLng(feature.geometry.paths[0][smallestDistFeatureIndex - 1][1], feature.geometry.paths[0][smallestDistFeatureIndex - 1][0]);
		leftDist = latlng.distanceTo(leftPoint);
	}

	if (smallestDistFeatureIndex != feature.geometry.paths[0].length - 1) {
    var rightPoint = L.latLng(feature.geometry.paths[0][smallestDistFeatureIndex + 1][1], feature.geometry.paths[0][smallestDistFeatureIndex + 1][0]);
    rightDist = latlng.distanceTo(rightPoint);
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

	return L.latLng(D.x, D.y);
}

//get a site and call callback when query is complete
function queryNWISsiteCallback (siteID, callback) {
  if (NWISmarkers[siteID]) {
    callback();
    return;
  }
  console.log('querying NWIS', siteID);
  
  var reqUrl = NWISsiteServiceURL;
  var siteTypeList = 'OC,OC-CO,ES,LK,ST,ST-CA,ST-DCH,ST-TS,AT,WE,SP';

  var requestData = {
    'format': 'mapper',
    'sites': siteID,
    'siteType': siteTypeList,
    'siteStatus': 'all'
  }

  $.ajax({
    url:reqUrl, 
    dataType: 'xml',
    data:  requestData, 
    type: 'GET',
    success: function(xml) {

      $(xml).find('site').each(function () {

        var siteID = $(this).attr('sno');
        var siteName = $(this).attr('sna');
        var lat = $(this).attr('lat');
        var lng = $(this).attr('lng');

        if (siteID.length <= 10) {

          if (!NWISmarkers[siteID]) {
            NWISmarkers[siteID] = {"siteName":siteName, "siteID":siteID, "latlng":L.latLng(lat, lng)}
          }
        }
      });
      callback();
    }
  });
}

function queryNWISsites(bounds) {
  console.log('querying NWIS', bounds);

  nwisSitesLayer.clearLayers();
  
  var reqUrl = NWISsiteServiceURL;
  var bbox = bounds.getSouthWest().lng.toFixed(7) + ',' + bounds.getSouthWest().lat.toFixed(7) + ',' + bounds.getNorthEast().lng.toFixed(7) + ',' + bounds.getNorthEast().lat.toFixed(7);
  var siteTypeList = 'OC,OC-CO,ES,LK,ST,ST-CA,ST-DCH,ST-TS,AT,WE,SP';

  var requestData = {
    'format': 'mapper',
    'bbox': bbox,
    'siteType': siteTypeList,
    'siteStatus': 'all'
  }

  $.ajax({
    url:reqUrl, 
    dataType: 'xml',
    data:  requestData, 
    type: 'GET',
    success: function(xml) {

      $(xml).find('site').each(function () {

        var siteID = $(this).attr('sno');
        var siteName = $(this).attr('sna');
        var lat = $(this).attr('lat');
        var lng = $(this).attr('lng');

        if (siteID.length <= 10) {

          var siteMarker = L.marker([lat, lng], {icon: siteIcon, draggable:false});

          /* var point = L.circle([lat, lng], {
            color: 'red',
            fillColor: '#f03',
            fillOpacity: 0.5,
            radius: 50
          }); */

          var tooltip = siteID + "<br>" + siteName;
          siteMarker.bindTooltip(tooltip, {sticky: true});

          if (!NWISmarkers[siteID]) {
            NWISmarkers[siteID] = {"siteName":siteName, "siteID":siteID, "latlng":L.latLng(lat, lng)}
          }
          nwisSitesLayer.addLayer(siteMarker);
        }
      });
    }
  });
}

function fillIDHTML (inStr) {
  var replaced = inStr.replace(/_\d*_/g, function(match) {return getSiteLinkHTML(match.substring(1, match.length-1));});
  return replaced;
}

function stripIDHTMLFormat (inStr) {
  var replaced = inStr.replace(/_\d*_/g, function(match) {return match.substring(1, match.length-1);});
  return replaced;
}

function getSiteLinkHTML (siteID) {
  var html = '<a href = "#0" class="' + idNumLinkClass + '">' + siteID + '</a>';
  return html;
}

function goToSite (siteID) {
  //catch cases when site doesn't exist in NWIS because its the new site ID suggestions
  if (currentResultsIDs && currentResultsIDs.includes(siteID)) {
    theMap.flyTo(currentResultsLatLng, siteHighlightZoomLevel);
  }
  else {
    if (!NWISmarkers[siteID]){
      queryNWISsiteCallback(siteID, function() { goToSite(siteID); });
      return;
    }
    var siteInfo = NWISmarkers[siteID];
    var latlng = siteInfo["latlng"];
    theMap.flyTo(latlng, siteHighlightZoomLevel);
  }

  console.log("going to " + siteID);
  $('body').toggleClass('isOpenMenu');
}

function highlightSite (siteID) {
  //catch cases when site doesn't exist in NWIS because its the new site ID suggestions
  if (currentResultsIDs && currentResultsIDs.includes(siteID)) {
    highlightLatLng(currentResultsLatLng, true);
  }
  else {
    if (!NWISmarkers[siteID]){
      queryNWISsiteCallback(siteID, function() { highlightSite(siteID); });
      return;
    }
    var siteInfo = NWISmarkers[siteID];
    var latlng =  siteInfo["latlng"];
    highlightLatLng(latlng, true);
  }
}

function highlightLatLng (latLng, clear) {
  if (clear) {
    highlightedLocationsLayer.clearLayers();
  }
  L.circle(latLng, {radius:120, color:"#c2134b"}).addTo(highlightedLocationsLayer)
}

function setBasemap(baseMap) {

  switch (baseMap) {
    case 'Sentinel': baseMap = 'Sentinel'; break;
    case 'Streets': baseMap = 'Streets'; break;
    case 'Satellite': baseMap = 'Imagery'; break;
    case 'Clarity': baseMap = 'ImageryClarity'; break;
    case 'Topo': baseMap = 'Topographic'; break;
    case 'Terrain': baseMap = 'Terrain'; break;
    case 'Gray': baseMap = 'Gray'; break;
    case 'DarkGray': baseMap = 'DarkGray'; break;
    case 'NatGeo': baseMap = 'NationalGeographic'; break;
  }

  if (baseMapLayer) theMap.removeLayer(baseMapLayer);
  baseMapLayer = basemapLayer(baseMap);
  theMap.addLayer(baseMapLayer);
  if (basemaplayerLabels) theMap.removeLayer(basemaplayerLabels);
  if (baseMap === 'Gray' || baseMap === 'DarkGray' || baseMap === 'Imagery' || baseMap === 'Terrain') {
    basemaplayerLabels = basemapLayer(baseMap + 'Labels');
    theMap.addLayer(basemaplayerLabels);
  }
}