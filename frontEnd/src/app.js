// ------------------------------------------------------------------------------
// ----- ADONNIS -----------------------------------------------------------------
// ------------------------------------------------------------------------------

// copyright:   2018 Martyn Smith - USGS NY WSC

// authors:  Martyn J. Smith - USGS NY WSC

// purpose:  USGS NY WSC Web App Template

// updates:
// 08.07.2018 - MJS - Created
// 04.24.2020 - MJS - Updates/modularized

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

var NHDstreamRadius = 3000;
//END user config variables 

//START global variables
var theMap;
var baseMapLayer, basemaplayerLabels;
var nwisSitesLayer;

var NHDlinesLayer;
var isQueryingLines;
var lastQueriedFeatures;
var lastQueryLatlng;

var cursor;
var cursorIcon;
var snappedCursorLatLng;

var confirmPopup;
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

  NHDlinesLayer = featureGroup().addTo(theMap);

  //hide laoding spinner
  $('#loading').hide();
  $('#highPriorityWarnings').hide();
  $('#mediumPriorityWarnings').hide();
  $('#adonnisResults').hide();
  $('#nhdFailure').hide();

  cursorIcon = L.divIcon({className: 'wmm-pin wmm-altblue wmm-icon-triangle wmm-icon-white wmm-size-25'});

}

function initListeners() {

  /*  START EVENT HANDLERS */
  theMap.on('zoomend dragend', function() {

    //only query if zoom is reasonable
    if (theMap.getZoom() >= 10) {
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
      if (theMap.getZoom() < 10) {
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
  /*  END EVENT HANDLERS */

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
}

function moveCursor (latlng) {
  $('#adonnisResults').hide();
  $('#latitude').val(latlng.lat);
  $('#longitude').val(latlng.lng);
  
  if(lastQueriedFeatures != null && latlng.distanceTo(lastQueryLatlng) < NHDstreamRadius/2) {
    var snappedLatLng = snapToFeature(latlng, lastQueriedFeatures);
    if (cursor == null) {
      cursor = L.marker(snappedLatLng, {icon: cursorIcon}).addTo(theMap);
      cursor.bindPopup('<p>Is this location correct?</p><button type="button" class="btn" id="notCorr">No</button><button type="button" class="btn btn-primary" id="yesCorr" style = "float:right;">Yes</button>');
      //confirmPopup = L.popup({offset: L.point(0,-50), closeOnClick: true, autoClose: true})
      //.setContent(),
      
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
    });
  }
  else {
    queryNHDStreams (latlng, function(){ moveCursor(latlng) });
  }
}

function displaySiteInfo (siteInfo)
{
  $('#adonnisResults').show();
  $('#initialAdvice').hide();

  $('#siteIdDisp').html(siteInfo["id"]);
  $('#storyDisp').html(siteInfo["story"]);

  var names = siteInfo["nameInfo"]["suggestedNames"];
  var namesHTML = ""
  for (var name of names){
    namesHTML += '<div class="alert alert-info" role="alert" id="namesDisp">';
    namesHTML += name
    namesHTML += '</div>';
  }

  $('#namesDisp').html(namesHTML);
  
  var log = siteInfo["log"];

  var numLowPriority = log["low priority"].length;
  var numMediumPriority = log["medium priority"].length;
  var numHighPriority = log["high priority"].length;
  var totalWarnings = numLowPriority + numMediumPriority + numHighPriority;

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

    for (var warningBody of log["high priority"]) {
      warningsHTML += '<div class="alert alert-danger">';
      warningsHTML += warningBody;
      warningsHTML += '</div>';
    }

    for (var warningBody of log["medium priority"]) {
      warningsHTML += '<div class="alert alert-warning">';
      warningsHTML += warningBody;
      warningsHTML += '</div>';
    }

    for (var warningBody of log["medium priority"]) {
      warningsHTML += '<div class="alert alert-warning">';
      warningsHTML += warningBody;
      warningsHTML += '</div>';
    }

    for (var warningBody of log["low priority"]) {
      warningsHTML += '<div class="alert alert-info">';
      warningsHTML += warningBody;
      warningsHTML += '</div>';
    }

    $('#warningsDisp').html(warningsHTML);
  }
  else {
    $('#warningSection').hide();
  }
}

function querySiteInfo (latLng, callback) {

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
			if (resultsJSON && resultsJSON.id.length > 0) {
				callback(resultsJSON);
			} else {
				console.log("couldn't read results");
      }
      $('#loading').hide();
    },
    error: function(jqXH, text, errorThrown){
      console.log("failed query: " + text + " error=" + errorThrown);
      console.log(jqXH.responseText);
      $('#loading').hide();
    },
  }); 
  //callback({"id": "01362012", "story": "Found an upstream site (01362032) and a downstream site (0136200705)", "log": {"low priority": [], "medium priority": ["0136200705 conflicts with 7 other sites. Consider changing this site's ID", "01362005 conflicts with 6 other sites. Consider changing this site's ID", "01362008 conflicts with 01362004. Consider changing the site ID of one of these two sites", "01362032 conflicts with 01362030. Consider changing the site ID of one of these two sites"], "high priority": ["01362032 is involved in a site conflict. See story/medium priority warnings for conflict details.", "0136200705 is involved in a site conflict. See story/medium priority warnings for conflict details.", "The found upstream site is larger than found downstream site. ADONNIS output almost certainly incorrect."]}});
}

//attempt to get streams in a radius around latlng. Send features to callback in format callback(results)
function queryNHDStreams (latlng, callback) {
  
  console.log('querying NHD', NHDstreamRadius);
  //var queryUrl = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/2/query?geometry=" + latlng.lng + "," + latlng.lat + "&outFields=GNIS_NAME%2C+LENGTHKM%2C+STREAMLEVE%2C+FCODE%2C+OBJECTID%2C+ARBOLATESU&geometryType=esriGeometryPoint&inSR=4326&outSR=4326&distance=" + NHDstreamRadius + "&units=esriSRUnit_Meter&returnGeometry=true&f=pjson";
	var queryUrl = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6/query?geometry=" + latlng.lng + "," + latlng.lat + "&outFields=GNIS_NAME%2CREACHCODE&geometryType=esriGeometryPoint&inSR=4326&outSR=4326&distance=" + NHDstreamRadius + "&units=esriSRUnit_Meter&outFields=*&returnGeometry=true&f=pjson";
	
	if (isQueryingLines == true) {
		console.log("already querying");
		return;
	}
  isQueryingLines = true;

  $('#loading').show();

	return $.ajax({
		url: queryUrl,
		dataType: 'json',
		timeout: 2000,
		success: function(results){
      console.log("query success")
      isQueryingLines = false;
      lastQueriedFeatures = results.features;
      lastQueryLatlng = latlng
      highlightFeature(lastQueriedFeatures);
      $('#loading').hide();
      $('#nhdFailure').hide();
      callback()
		},
		error: function(jqXH, text, errorThrown){
      console.log("failed query: " + text + " error=" + errorThrown);
      console.log(jqXH.responseText);

      isQueryingLines = false;
      $('#loading').hide();
      $('#nhdFailure').show();
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
		console.error("found no nearest feature returning [-1, -1]");
		return [-1, -1];
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
  var NWISmarkers = {};

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

          // var myIcon = L.divIcon({className: 'wmm-pin wmm-red wmm-icon-circle wmm-icon-white wmm-size-25'});
          // var point = L.marker([lat, lng], {icon: myIcon});


          var point = L.circle([lat, lng], {
            color: 'red',
            fillColor: '#f03',
            fillOpacity: 0.5,
            radius: 50
          });


          var tooltip = siteID + "<br>" + siteName;
          point.bindTooltip(tooltip, {sticky: true});

          if (!NWISmarkers[siteID]) {
            NWISmarkers[siteID] = point;
            NWISmarkers[siteID].data = { siteName: siteName, siteCode: siteID };
            nwisSitesLayer.addLayer(NWISmarkers[siteID]);
          }

        }
      });
    }
  });
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