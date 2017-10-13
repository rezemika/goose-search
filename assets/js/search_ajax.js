// Requests the results to the server.
// Thanks to vhf for his precious help for the debug.

function request_results (radius, userLatitude, userLongitude, searchPresetId, noPrivate) {
    window.map_results = [];
    console.log('Starting request...')
    $.ajax({
        url: '/getresults/', // Destination URL.
        type: 'POST', // HTTP method.
        data: { // Data sent with the post request.
            radius: radius,
            user_latitude: userLatitude,
            user_longitude: userLongitude,
            search_preset_id: searchPresetId,
            no_private: noPrivate,
        },

        // Handles a successful response.
        success: function (json) {
            // Logs the returned json to the console.
            console.log('received:', JSON.stringify(json, null, 2));
            if (json.status != "ok") {
                console.log('Error : Request status != "ok"');
                console.log(json.debug_msg);
                $('#geo_results').html("<center><em>" + json.err_msg + "</em></center>");
                $('#geo_results').attr("aria-live", "assertive");
                $('#geo_results').attr("aria-busy", "false");
                return
            }
            if (!json.content.length) {
                console.log('json content is empty')
                $('#geo_results').html("<center><em>Pas de résultats.</em></center>");
                $('#geo_results').attr("aria-live", "assertive");
                $('#geo_results').attr("aria-busy", "false");
                console.log('Success, but no results !');
                return
            }
            // Fills the page.
            $('#geo_results').html('<ul id="results_list">' + json.content.join('') + '</ul>');
            window.map_results = json.map_data;
            console.log('Map data: ' + map_results);
            // Enables the button to load the map.
            $('#map_getter').prop("disabled", false);
            // Hides all the links to the map, as it is not loaded yet.
            $('.seeonmap-link').hide();
            // Updates the ARIA.
            $('#geo_results').attr("aria-live", "assertive");
            $('#geo_results').attr("aria-busy", "false");
            // Makes popovers open on top on small screens.
            if ($(document).width() < 768) {
                console.log("Small screen detected, popovers will open on top.");
                var popovers = document.querySelectorAll('[data-toggle="popover"]');
                for (i=0; i < popovers.length; i++) {
                        popovers[i].setAttribute("data-placement", "top");
                }
            }
            // Enables popovers.
            $('[data-toggle="popover"]').popover();
            // Loads filters.
            $('#results_filters').html(json.filters);
            console.log(json.filters);
            console.log('Success !');
        },

        // Handles a non-successful response.
        error: function (xhr, errmsg, err) {
            $('#geo_results').html("<center><em>Erreur 500.</em></center><br/><center><em>Désolé, une erreur non prise en charge s'est produite.</em></center>")
            // Provides a bit more info about the error to the console.
            console.log(JSON.stringify(xhr, null, 2));
            $('#map_getter').prop("disabled", false);
        },
    })
};
