function load_map(startCoordinates, startZoom, userCoords, youAreHereMsg, mapCopyright) {
    console.log("Loading the map.");
    window.map = L.map("leaflet-map", {
        // See https://github.com/Leaflet/Leaflet.fullscreen
        fullscreenControl: true,
    }).setView(startCoordinates, startZoom);
    L.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png", {
        attribution: mapCopyright
    }).addTo(window.map);
    
    console.log("Completed. Adding markers.");
    var allMarkers = new L.FeatureGroup();
    window.map_results.forEach(function(result) {
        marker_coords = [result[1][0], result[1][1]];
        marker = new L.marker(marker_coords, {result_id: result[3]});
        marker.bindPopup('');
        var popup = marker.getPopup();
        popup.setContent(result[2]);
        allMarkers.addLayer(marker);
    });
    window.allMarkers = allMarkers;
    window.map.addLayer(allMarkers);
    
    console.log("Completed. Adding the 'You are here' red marker.");
    var redIcon = new L.Icon({
        iconUrl: "/static/images/colored_markers/marker-icon-2x-red.png",
        shadowUrl: "/static/images/colored_markers/marker-shadow.png",
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });
    
    var user_marker = new L.marker([
        userCoords[0],
        userCoords[1]
    ], {icon: redIcon}).addTo(window.map);
    user_marker.bindPopup(youAreHereMsg);
    
    console.log("Adapting the size of the map to the size of the screen.");
    window.map.fitBounds(allMarkers.getBounds());
    L.control.scale().addTo(window.map);
    window.map.setZoom(startZoom);
    $("#map-collapse").on("shown.bs.collapse", function() {
        window.map.invalidateSize();
    });
    // Opens the map.
    $("#map-collapse").collapse("show")
    console.log("Done!");
}

function update_map_size() {
    box_height = $(window).height() * 0.75;
    box_width = ($("#map-panel").width() * 0.9) + 10;
    $("#leaflet-map").height(box_height).width(box_width);
    window.map.invalidateSize();
}

function see_on_map(markerId) {
    console.log("Searching for ID " + markerId);
    window.allMarkers.eachLayer(function(marker){
        if (marker.options.result_id == markerId) {
            console.log("Found ! ID : " + marker.options.result_id);
            marker.openPopup();
            $("#map-collapse").collapse("show");
            $(document).scrollTop($("#map-collapse").offset().top);
            return;
        }
    });
    console.log("Error : ID " + markerId + " not found!");
}
