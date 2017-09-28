// Allows to filter the results a posteriori with checkboxes.

function filter_results_handler (object) {
    var ul, li, filters, spans, last_span, result_tags, active_filters, show_result;
    var i, j;
    ul = document.getElementById("results_list");
    li = ul.getElementsByTagName("li");
    filters = document.getElementsByName("result_filter");
    active_filters = []
    // Stores the values of the active filters (those ticked).
    for (i = 0; i < filters.length; i++) {
        if (filters[i].checked) {
            active_filters.push(filters[i].value);
        }
    }
    console.log("Active filters: " + active_filters);
    for (i = 0; i < li.length; i++) {
        span = li[i].getElementsByClassName("result_tags")[0];
        result_tags = span.innerHTML.split(';');
        // Checks all the result tags are included in the active filters.
        show_result = result_tags.every(tag => active_filters.indexOf(tag) > -1);
        if (show_result == true) {
            console.log("Result " + i + ": showed");
            li[i].style.display = "block";
        }
        else {
            console.log("Result " + i + ": hidden");
            li[i].style.display = "none";
        }
        console.log("Tags: " + result_tags);
        console.log('');
    }
    return
}
