// Allows to filter the results a posteriori with checkboxes.

function filter_results_handler (object) {
    var ul, li, filters, span, lastSpan, resultTags, activeFilters, showResult, blockId;
    var i, j;
    ul = document.getElementById("results_list");
    li = ul.getElementsByTagName("li");
    filters = document.getElementsByName("result_filter");
    activeFilters = [];
    // Stores the values of the active filters (those ticked).
    for (i = 0; i < filters.length; i++) {
        if (filters[i].checked) {
            activeFilters.push(filters[i].value);
        }
    }
    console.log("Used filter: " + object.value);
    console.log("Active filters: " + activeFilters);
    for (i = 0; i < li.length; i++) {
        span = li[i].getElementsByClassName("result_tags")[0];
        resultTags = span.innerHTML.split(';');
        blockId = li[i].children[0].id.replace("block", "map");
        if (window.map) {
            var resultMarker;
            window.allMarkers.eachLayer(function(marker) {
                if (marker.options.result_id == blockId) {
                    resultMarker = marker;
                }
            });
        }
        // Checks all the result tags are included in the active filters.
        showResult = resultTags.every(tag => activeFilters.indexOf(tag) > -1);
        if (showResult == true) {
            console.log("Result " + i + ": showed");
            li[i].style.display = "block";
            if (window.map) {
                resultMarker.addTo(window.map);
            }
        }
        else {
            console.log("Result " + i + ": hidden");
            li[i].style.display = "none";
            if (window.map) {
                resultMarker.remove(window.map);
            }
        }
        console.log("Tags: " + resultTags);
        console.log();
    }
    return;
}
