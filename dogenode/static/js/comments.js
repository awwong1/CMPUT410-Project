// Sends an ajax put request to add a comment for a post
function putComment() {
    console.log("got here");
    var guid = $(this).attr("id");
    var comment = $("form#"+guid+" input[type='text']").val();
    JSONData = JSON.stringify({"comment":comment, "post_id":guid}) 
    $("form#"+guid+" input[type='text']").val("");
    // send ajax request
    $.ajax({
        type: "PUT",
        url: location.origin+"/comments/add_comment/",
        data: JSONData, 
        dataType: "json",
        contentType: "application/json",
        success: function(response) {
            addComment(response);
        },
        error: function(xhr, status, error) {
            console.log(xhr.responseText);
        }
    });
}

// Create new html for the new comment and add it
function addComment(data) {
    $("table."+data["postGuid"]+" > tbody:last").append('<tr>'
    + '<td><small>'
    +  '<a href="/author/' +data["author"]["id"] + '/">'
    +  '<strong>'+data["author"]["displayname"]+'</strong>'
    +  '</a> on ' + data["pubDate"] + '</small>: ' + data["comment"]
    + '</td></tr>');
}


