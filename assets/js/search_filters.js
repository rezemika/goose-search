// Allows to filter the results a posteriori with checkboxes.

function filter_results_handler (object) {
    var input, filter, status, ul, li, tags, i, spans, filter, tags_field, tags_array;
    filter = object.value;
    status = object.checked;
    console.log('Filter "' + object.value + '" used (now ' + status + ').');
    ul = document.getElementById("results_list");
    li = ul.getElementsByTagName("li");
    for (i = 0; i < li.length; i++) {
        spans = li[i].getElementsByTagName("span");
        var last_span = spans[spans.length - 1];
        tags_field = last_span.innerHTML;
        tags_array = tags_field.split(';');
        console.log('Result ' + i + '. Tags: ' + tags_array);
        // Is the tag present in this result?
        console.log(tags_array.indexOf(filter) != -1);
        console.log('');
        if (tags_array.indexOf(filter) != -1) {
            if (status == true) {
                li[i].style.display = "block";
            }
            else {
                li[i].style.display = "none";
            }
        }
    }
    return
}
