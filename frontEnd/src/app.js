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
import { nativeTemplateEngine } from 'knockout';

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

var NHDlinesLayer;
var isQueryingLines;
var lastQueriedFeatures;
var lastQueryLatlng; //last query of NHD data. Not nec the same as last query of backend
var lastQueryWarnings;

var highlightedSites;

var cursor;
var cursorIcon;
var siteIcon;
var highlightedIcon;
var snappedCursorLatLng;
var currentResultsIDs = []; //these are the ID(s) that are displayed as results. Keep track so we can hyperlink them properly
var currentResultsLatLng;

var idNumLinkClass = "idNum"
var simulateBackendResponse = false;
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
  $('#frontEndFailure').hide();

  cursorIcon = L.divIcon({className: 'wmm-pin wmm-yellow wmm-icon-diamond wmm-icon-blue wmm-size-25'});
  siteIcon = L.divIcon({className: 'wmm-pin wmm-altblue wmm-icon-diamond wmm-icon-blue wmm-size-25'});
  highlightedIcon = L.divIcon({className: 'wmm-pin wmm-red wmm-icon-noicon wmm-icon-white wmm-size-30'});
  NWISmarkers = {};
  lastQueryWarnings = [];
  highlightedSites = [];
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
  //go to sites from site links
  $("#adonnisResults").on("click", "[class='" + idNumLinkClass + "']", function(event){
    var siteID = $( this ).text();
    goToSite(siteID);
  });

  $("#adonnisResults").on("mouseover", "[class='" + idNumLinkClass + "']", function(event){
    var siteID = $( this ).text();
    highlightSite(siteID);
  });

  $("#adonnisResults").on("mouseleave", "[class='" + idNumLinkClass + "']", function(event){
    clearHighlightedSites();
  });
  //display warning previews
  $("#adonnisResults").on("click", "[class~='adonnisWarning']", function(event){
    console.log("clicked on alert");
    var warningNumber = $( this ).data("warning");
    if (warningNumber != undefined && warningNumber != null) {
      displayWarningConflicts(lastQueryWarnings[warningNumber]);
    }
  });

  /*  END EVENT HANDLERS */

  $('.leaflet-container').css('cursor','crosshair');
}

function moveCursor (latlng, snap = true) {
  
  $('#adonnisResults').hide();
  $('#latitude').val(latlng.lat);
  $('#longitude').val(latlng.lng);
  if (queriedNetworkLayer != null) 
  {
    queriedNetworkLayer.clearLayers();
  }
   
  if(lastQueriedFeatures != null && latlng.distanceTo(lastQueryLatlng) < NHDstreamRadius/2 || snap == false) {
    var snappedLatLng = latlng;
    if (snap == true) {
      snappedLatLng = snapToFeature(latlng, lastQueriedFeatures);
    }
    
    if (cursor == null) {
      cursor = L.marker(snappedLatLng, {icon: cursorIcon, riseOnHover: true}).addTo(theMap);
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
  lastQueryWarnings = [];
  $('#adonnisResults').show();
  $('#highPriorityWarnings').hide();
  $('#mediumPriorityWarnings').hide();
  $('#initialAdvice').hide();

  var names = siteInfo["names"];
  var namesHTML = ""
  for (var name of names){
    namesHTML += getAlertHTML(name, "secondary");
  }

  $('#namesDisp').html(namesHTML);
  
  var log = siteInfo["log"];

  if (simulateBackendResponse) {
    var debugWarning = {"body": "_01387135_ conflicts with 3 other sites. Consider changing this site's ID", "responsibleSite": "01387135", "implicatedSites": ["01387125", "01387095", "01387100"]};
    
    log["mediumPriority"].push(debugWarning);
  }

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
      warningsHTML += getWarningHTML(fillIDHTML(warning["body"]), "danger", warning);
    }

    for (var warning of log["mediumPriority"]) {
      warningsHTML += getWarningHTML(fillIDHTML(warning["body"]), "warning", warning);
    }

    for (var warning of log["lowPriority"]) {

      warningsHTML += getWarningHTML(fillIDHTML(warning["body"]), "info", warning);
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
      },
      onEachFeature: function (feature, layer) {
        if (feature.properties && feature.properties.streamNm) {
          layer.bindTooltip(feature.properties.streamNm, {sticky:true});
        }
      }
    }).addTo(theMap);
    NHDlinesLayer.clearLayers();
  }

  if ("snaps" in siteInfo) {
    var snapInfo = siteInfo["snaps"]
    var allSites = []
    for (var site in snapInfo) {
      //check if site is a key of snapInfo dict
      if (snapInfo.hasOwnProperty(site)) { 
        allSites.push(site)
      }
    }
    queryNWISsiteCallback(allSites, function () {
      for (site of allSites) {
        var originalLatLng = tryGetSiteLatLng(site);
        //switch order of tuple. Backend deals with (long, lat) usuaully to be consistant with x,y coordinates
        var snapLatLng = L.latLng(snapInfo[site][1], snapInfo[site][0]);
        if (originalLatLng != null) {
          L.polyline([originalLatLng, snapLatLng], {color:"#ffffff", dashArray:"1 8"}).addTo(queriedNetworkLayer);
        }
      }
    });
  }
}

function displayWarningConflicts (warning) {
  var implicatedSites = warning["implicatedSites"];
  var responsibleSite = warning["responsibleSite"];
  if (implicatedSites == null || responsibleSite == null) {
    return;
  }

  var allInvolvedSites = implicatedSites.concat(responsibleSite);

  if (!areSitesLoaded(allInvolvedSites)) {
    queryNWISsiteCallback(allInvolvedSites, function () {displayWarningConflicts(warning);});
  }
  var responsibleSiteLatLng = tryGetSiteLatLng(responsibleSite);
  if (responsibleSiteLatLng == null) {
    return;
  }
  highlightSite(responsibleSite)
  var foundLatLngs = [responsibleSiteLatLng];
  for (var implicatedSite of implicatedSites) {
    var implicatedSiteLatLng = tryGetSiteLatLng(implicatedSite);
    if (implicatedSiteLatLng == null) {
      continue;
    }
    foundLatLngs.push(implicatedSiteLatLng);
    highlightSite(implicatedSite)
  }
  theMap.fitBounds(L.latLngBounds(foundLatLngs));
}

function querySiteInfo (latLng, callback) {
  $('#frontEndFailure').hide();
  if (simulateBackendResponse) {
    callback({"idInfo": {"id": "_01433466_", 
    "story": "Requested site info at 41.501755, -74.713887. Found a upstream site _01433455_ and a downstream site _0143349805_. New site is the weighted average of these two sites."}, 
    "idInfoAlt": null, 
    "log": {"lowPriority": [], "mediumPriority": [], "highPriority": []}, 
    "names": ["BUSH KILL AT HARTWOOD CLUB NY", "BUSH KILL NEAR SOURCE AT HARTWOOD CLUB NY"], 
    "network": {"type": "FeatureCollection", 
    "crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, 
    "features": [
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.73694206929225, 41.484324439856785, 0, 39.03338000000001], [-74.7368868175124, 41.483926824896564, 0, 36.947630000000004]]}, "properties": {"streamLevel": 4, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72313162882901, 41.50226244490796, 0, 98.68699000000001], [-74.72304000246665, 41.501656980354944, 0, 97.23882000000002]]}, "properties": {"streamLevel": 3, "streamNm": "Bush Kill"}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.69107853215587, 41.48441527609562, 0, 100.00000000000001], [-74.69162619545874, 41.48344340046901, 0, 0]]}, "properties": {"streamLevel": 2, "streamNm": "Steeny Kill"}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.74476091749034, 41.506746200267905, 0, 100.00000000000001], [-74.75043351126075, 41.5054813090628], [-74.75645098354012, 41.50288599185341, 0, 0]]}, "properties": {"streamLevel": 3, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.69716072041578, 41.5278952023253, 0, 69.10762000000001], [-74.69180937452158, 41.53348923780309], [-74.68729995037292, 41.534651259208324, 0, 0]]}, "properties": {"streamLevel": 4, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72297796032156, 41.50151199719895, 0, 96.87899000000002], [-74.72270194756062, 41.50108204391923, 0, 95.74820000000001]]}, "properties": {"streamLevel": 3, "streamNm": "Bush Kill"}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72586079330718, 41.513343402535014, 0, 100.00000000000001], [-74.72504498019707, 41.511356040562944, 0, 0]]}, "properties": {"streamLevel": 5, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72978202755725, 41.48011196153915, 0, 35.92069000000001], [-74.73070232192143, 41.47935026150612, 0, 33.462360000000004]]}, "properties": {"streamLevel": 3, "streamNm": "Bush Kill"}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72270194756062, 41.50108204391923, 0, 95.74820000000001], [-74.72000980855853, 41.49772875056232], [-74.72152741713796, 41.49537149025085], [-74.72183502403244, 41.491892456908595], [-74.72231286526652, 41.489563414110705], [-74.72409262547372, 41.48706988273783], [-74.72614218441005, 41.48397674986466], [-74.72978202755725, 41.48011196153915, 0, 35.92069000000001]]}, "properties": {"streamLevel": 3, "streamNm": "Bush Kill"}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.70132532085275, 41.52612660523745, 0, 100.00000000000001], [-74.69730679097256, 41.527867675874404, 0, 69.8662]]}, "properties": {"streamLevel": 4, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.71492300252747, 41.50223695548159, 0, 100.00000000000001], [-74.71961401033103, 41.50459303436789, 0, 0]]}, "properties": {"streamLevel": 3, "streamNm": "Bush Kill"}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72996898403586, 41.473709980587095, 0, 18.119940000000003], [-74.72980901025343, 41.47199998642292, 0, 14.046460000000002]]}, "properties": {"streamLevel": 3, "streamNm": "Bush Kill"}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72276699277373, 41.50321420107964, 0, 14.070930000000002], [-74.72277101093798, 41.50303501189814, 0, 8.581040000000002]]}, "properties": {"streamLevel": 3, "streamNm": "Bush Kill"}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.7401181348445, 41.5168315241417, 0, 71.67193000000002], [-74.74031532852409, 41.51696915957506, 0, 68.34257000000001]]}, "properties": {"streamLevel": 4, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.71000519167423, 41.525004996892704, 0, 100.00000000000001], [-74.70358959010338, 41.5231776738112, 0, 0]]}, "properties": {"streamLevel": 5, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.71926505526734, 41.471575973179846, 0, 67.90608], [-74.71977303010262, 41.47122699812198, 0, 65.15879000000001]]}, "properties": {"streamLevel": 4, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.73770580257379, 41.48586714802557, 0, 47.490520000000004], [-74.73694206929225, 41.484324439856785, 0, 39.03338000000001]]}, "properties": {"streamLevel": 4, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.73100404895737, 41.47896601579112, 0, 32.40914000000001], [-74.72996898403586, 41.473709980587095, 0, 18.119940000000003]]}, "properties": {"streamLevel": 3, "streamNm": "Bush Kill"}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.6956523879683, 41.502302072008256, 0, 90.54073000000001], [-74.7029343912745, 41.50280100433103, 0, 0]]}, "properties": {"streamLevel": 4, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72276699277373, 41.50321420107964, 0, 100.00000000000001], [-74.72287472682743, 41.50313667630654, 0, 63.462770000000006]]}, "properties": {"streamLevel": 5, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.73903311550835, 41.51582304315643, 0, 93.82047000000001], [-74.7401181348445, 41.5168315241417, 0, 71.67193000000002]]}, "properties": {"streamLevel": 4, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.71826560046202, 41.533431610800704, 0, 100.00000000000001], [-74.7211899708277, 41.533198934418266], [-74.7242261074251, 41.52939192138699], [-74.72754541366129, 41.527517618909584], [-74.73269706514579, 41.52720860086994], [-74.73490903088732, 41.52877403852127, 0, 0]]}, "properties": {"streamLevel": 3, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.7029343912745, 41.50280100433103, 0, 100.00000000000001], [-74.71207900550822, 41.501560976431094, 0, 22.4932]]}, "properties": {"streamLevel": 3, "streamNm": "Bush Kill"}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.69730679097256, 41.527867675874404, 0, 69.8662], [-74.69716072041578, 41.5278952023253, 0, 69.10762000000001]]}, "properties": {"streamLevel": 4, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72293794037566, 41.50278459481369, 0, 100.00000000000001], [-74.72313162882901, 41.50226244490796, 0, 98.68699000000001]]}, "properties": {"streamLevel": 3, "streamNm": "Bush Kill"}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72936833360598, 41.53755159791312, 0, 100.00000000000001], [-74.72976092792784, 41.534350265729294], [-74.73173839475268, 41.53021487117429], [-74.73490903088732, 41.52877403852127, 0, 0]]}, "properties": {"streamLevel": 4, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72287472682743, 41.50313667630654, 0, 63.462770000000006], [-74.72311573493668, 41.503070802411386, 0, 0]]}, "properties": {"streamLevel": 5, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.6942189327947, 41.49058140363039, 0, 100.00000000000001], [-74.69107853215587, 41.48441527609562, 0, 0]]}, "properties": {"streamLevel": 3, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.72504498019707, 41.511356040562944, 0, 100.00000000000001], [-74.72396139726706, 41.510239873237836, 0, 0]]}, "properties": {"streamLevel": 5, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.73876364248267, 41.51550690845849, 0, 100.00000000000001], [-74.73903311550835, 41.51582304315643, 0, 93.82047000000001]]}, "properties": {"streamLevel": 4, "streamNm": ""}}, 
      {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-74.73791624820043, 41.48598793349669, 0, 48.47690000000001], [-74.73770580257379, 41.48586714802557, 0, 47.490520000000004]]}, "properties": {"streamLevel": 4, "streamNm": ""}}]}}, latLng);
      
    return;
  }
  
  $('#loading').show();
  console.log("attemping site info query");
	return $.ajax({ 
		type : 'get',
		url: "./siteID.php",
		dataType: 'json',
		data:
        {
				'lat' : latLng.lat,
				'lng' : latLng.lng
        },
		success: function(theResult){
			if (theResult) {
				callback(theResult, latLng);
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

function getWarningHTML (body, alertTag, warning) {
  if (warning["implicatedSites"]) {
    var warningNumber = lastQueryWarnings.length;
    lastQueryWarnings.push(warning);
    var wrappedBody = '<div class="container">' + 
                        '<div class="row">'+ 
                          '<div class="col-10">' + 
                            body + 
                          '</div>' + 
                          '<div class="col p-0 m-0">' + 
                          '<button type="button" class="btn btn-outline-secondary btn-sm btn-block adonnisWarning" data-warning="'+ warningNumber + '">' + 
                            'Go' + 
                          '</button>' + 
                          '</div>'+
                        '</div>'+
                      '</div>';
    return getAlertHTML(wrappedBody, alertTag);
  }
  else {
    return getAlertHTML(body, alertTag);
  }
}

//attempt to get streams in a radius around latlng. Send features to callback in format callback(results)
function queryNHDStreams (latlng, callback, retryService, failureCallback) {
  
  console.log('querying NHD', NHDstreamRadius);

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

function areSitesLoaded (siteIDs) {
  for (var siteID of siteIDs) {
    if (!NWISmarkers[siteID] && (!currentResultsIDs || !currentResultsIDs.includes(siteID))) {
      return false;
    }
  }
  return true;
}

//get a site and call callback when query is complete
function queryNWISsiteCallback (siteIDs, callback) {
  var missingSiteIDs = [];
  for (var reqID of siteIDs) {
    if (!NWISmarkers[reqID]) {
      missingSiteIDs.push(reqID);
    }
  }
  if (missingSiteIDs.length == 0) {
    callback();
    return;
  }
  console.log('querying NWIS', missingSiteIDs);
  
  var reqUrl = NWISsiteServiceURL;
  var siteTypeList = 'OC,OC-CO,ES,LK,ST,ST-CA,ST-DCH,ST-TS,AT,WE,SP';

  var requestData = {
    'format': 'mapper',
    'sites': missingSiteIDs.toString(),
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
          var thisIcon = siteIcon;
          if (highlightedSites.includes(siteID)){
            thisIcon = highlightedIcon;
          }
          var siteMarker = L.marker([lat, lng], {icon: thisIcon, draggable:false});

          var tooltip = siteID + "<br>" + siteName;
          siteMarker.bindTooltip(tooltip, {sticky: true});

          if (!NWISmarkers[siteID]) {
            NWISmarkers[siteID] = {"siteName":siteName, "siteID":siteID, "latlng":L.latLng(lat, lng), "marker":null}
          }
          nwisSitesLayer.addLayer(siteMarker);
          NWISmarkers[siteID]["marker"] = siteMarker
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


//we expect the callback to have f(latLng) as a signature
function getSiteLatLngThenCall (siteID, callback) {
  if (currentResultsIDs && currentResultsIDs.includes(siteID)) {
    callback(currentResultsLatLng);
  }
  else {
    if (!NWISmarkers[siteID]){
      queryNWISsiteCallback([siteID], function() { getSiteLatLngThenCall(siteID, callback); });
      return;
    }
    var siteInfo = NWISmarkers[siteID];
    var latlng = siteInfo["latlng"];
    callback(latlng);
  }
}
//might not be loaded. recommend calling queryNWISsiteCallback first
function tryGetSiteLatLng (siteID) {
  var siteInfo = NWISmarkers[siteID];
  if (siteInfo) {
    var latlng = siteInfo["latlng"];
    return latlng;
  }
  return null;
}

function goToSite (siteID) {

  getSiteLatLngThenCall(siteID, function (latlng) {
    theMap.flyTo(latlng, siteHighlightZoomLevel);
  });

  console.log("going to " + siteID);
  $('body').toggleClass('isOpenMenu');
}

function highlightSite (siteID) {
  highlightedSites.push(siteID);
  if (currentResultsIDs && currentResultsIDs.includes(siteID) && cursor) {
    cursor.setIcon(highlightedIcon);
  }
  else {
    if(NWISmarkers[siteID] && NWISmarkers[siteID]["marker"]) {
      NWISmarkers[siteID]["marker"].setIcon(highlightedIcon);
    }
  }

  // getSiteLatLngThenCall(siteID, function (latlng) {
  //   highlightLatLng(latlng, true);
  // });
}

function clearHighlightedSites () {
  cursor.setIcon(cursorIcon);
  for (var site in NWISmarkers) {
    //check if site is a key of snapInfo dict
    if (NWISmarkers.hasOwnProperty(site)) { 
      if(NWISmarkers[site].marker){
        NWISmarkers[site].marker.setIcon(siteIcon);
      }
    }
  }
  highlightedSites = [];

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