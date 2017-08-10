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
        spans = li[i].getElementsByTagName("span");
        last_span = spans[spans.length - 1];
        result_tags = last_span.innerHTML.split(';');
        // Checks all the result tags are in the active filters.
        show_result = true;
        for (j = 0; j < result_tags.length; j++) {
            if (active_filters.indexOf(result_tags[j]) == -1) {
                show_result = false;
            }
        }
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
