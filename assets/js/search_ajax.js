// Request the results to the server.
// Thanks to vhf for his precious help for the debug.

function request_results (radius, userLatitude, userLongitude, searchedTargetId, no_private, was_limited) {
  
  if (was_limited == true) {
    $('#geo_results').html("<center><em>Trop peu de requêtes ont été faites en trop peu de temps. Merci d'attendre quelques secondes avant de raffraichir la page.</em></center>")
    $('#geo_results').attr("aria-live", "assertive");
    $('#geo_results').attr("aria-busy", "false");
    console.log("Request blocked : too much requests in too little time.");
    return
  }
  
  console.log('Starting request...')
  $.ajax({
    url: '/getresults/', // Destination URL.
    type: 'POST', // HTTP method.
    data: { // Data sent with the post request.
      radius: radius,
      user_latitude: userLatitude,
      user_longitude: userLongitude,
      searched_target_id: searchedTargetId,
      no_private: no_private,
    },

    // Handles a successful response.
    success: function (json) {
      // Logs the returned json to the console.
      console.log('received:', JSON.stringify(json, null, 2))
      if (json.status != "ok") {
        console.log('Error : Request status != "ok"');
        console.log(json.debug_msg)
        $('#geo_results').html("<center><em>" + json.err_msg + "</em></center>")
        $('#geo_results').attr("aria-live", "assertive");
        $('#geo_results').attr("aria-busy", "false");
        return
      }
      if (!json.content.length) {
        console.log('json content is empty')
        $('#geo_results').html("<center><em>Pas de résultats.</em></center>")
        $('#geo_results').attr("aria-live", "assertive");
        $('#geo_results').attr("aria-busy", "false");
        console.log('Success, but no results !')
        return
      }
      // Allowings linebreaks.
      const htmlOutput = json.content.map(part => '\n\n' + part.replace(/\r?\n/g, '<br>\n')).join('')
      $('#geo_results').html('<ul style="list-style:none" id="results_list">' + htmlOutput + '</ul>')
      $('#geo_results').attr("aria-live", "assertive");
      $('#geo_results').attr("aria-busy", "false");
      $('[data-toggle="popover"]').popover();
      $('#results_filters').html(json.filters);
      console.log(json.filters);
      console.log('Success !')
    },

    // Handles a non-successful response.
    error: function (xhr, errmsg, err) {
      if (errmsg || err) $('#geo_results').html({errmsg, err})
      // Provide a bit more info about the error to the console.
      console.log(JSON.stringify(xhr, null, 2))
    },
  })
};
