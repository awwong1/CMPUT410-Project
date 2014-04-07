/* Sends an ajax put request to add a comment to a post 
    In the body of the request, a json object containing post guid
    and comment text is sent.

    Eg. {"postguid":"fa9fd4fc-ca64-4a31-adf8-c92f028bdc24",
         "comment": "this is the comment text"}

    A json representation of the new comment created is returned
    so it can be dynamically displayed on the page.

    Eg of json comment returned:
    {
        "guid": "f1617724-8ccc-4a27-9a99-fe84ca3c6aab", 
        "comment": "That we do!", 
        "pub_date": "Sat Apr 05 05:39:22 UTC 2014", 
        "author": {
            "id": "8faaa243-163b-4426-8b51-d45bc8cd3f4c", 
            "host": "http://cs410.cs.ualberta.ca:41011", 
            "displayname": "pepper", 
            "url": "http://cs410.cs.ualberta.ca:41011/author/8faaa243-163b-4426-8b51-d45bc8cd3f4c"
    }

*/
function putComment() {
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

/* 
    Create new html for the new comment and dynamically add it to the page
    to the corresponding post.
*/
function addComment(data) {
    $("table."+data["postGuid"]+" > tbody:last").append('<tr>'
    + '<td><small>'
    +  '<a href="/author/' +data["author"]["id"] + '/">'
    +  '<strong>'+data["author"]["displayname"]+'</strong>'
    +  '</a> on ' + data["pubDate"] + '</small>: ' + data["comment"]
    + '</td></tr>');
}


