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
//END user config variables 

//START global variables
var theMap;
var baseMapLayer, basemaplayerLabels;
var nwisSitesLayer;
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
  theMap = map('mapDiv', { zoomControl: false, minZoom: 8, });

  //add zoom control with your options
  control.zoom({ position: 'topright' }).addTo(theMap);
  control.scale().addTo(theMap);

  //basemap
  baseMapLayer = basemapLayer('ImageryClarity').addTo(theMap);;

  //set initial view
  theMap.setView([MapY, MapX], MapZoom);

  //define layers
  nwisSitesLayer = featureGroup().addTo(theMap);

  //hide laoding spinner
  $('#loading').hide();
}

function initListeners() {

  /*  START EVENT HANDLERS */
  theMap.on('zoomend dragend', function() {

    //only query if zoom is reasonable
    if (theMap.getZoom() >= 10) {
      queryNWISsites(theMap.getBounds());
    }
  });


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
    //do something
  });
  /*  END EVENT HANDLERS */
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

        var myIcon = L.divIcon({className: 'wmm-pin wmm-red wmm-icon-circle wmm-icon-white wmm-size-25'});
        NWISmarkers[siteID] = L.marker([lat, lng], {icon: myIcon});
        NWISmarkers[siteID].data = { siteName: siteName, siteCode: siteID };

        nwisSitesLayer.addLayer(NWISmarkers[siteID]);

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