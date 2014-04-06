$(document).ready(function() {
    /* the CSRF stuff is from:
     * https://docs.djangoproject.com/en/1.6/ref/contrib/csrf/#ajax
     * TODO: find a better way to do this cleanly...
     */
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    var csrftoken = getCookie('csrftoken');
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    // Adds a comment to the html page
    function addComment(data) {
        $("div#"+data["guid"]+" table tr:last").after('<tr>'
        + '<td><small>'
        +  '<a href="/author/' +data["author"]["id"] + '/">'
        +  '<strong>'+data["author"]["displayname"]'</strong>'
        +  '</a> on ' + data["pubDate"] + '</small>'
        + '</td></tr>');
    }

    $(".makeComment").on("click", function() {
        var guid = $(this).attr("id");
        var comInputs = $("form#"+guid+" :input");
        var comment = $("form#"+guid+" > input[type='text']").val();
        JSONData = JSON.stringify({"comment":comment}) 
        // send ajax request
        $.ajax({
            type: "PUT",
            url: location.origin+"/comments/add_comment",
            data: JSONData, 
            dataType: "json",
            contentType: "application/json",
            success: function(response) {
                addComment(response[0]);
            },
            error: function(xhr, status, error) {
                console.log(xhr.responseText);
            }
        });
        return false;
    });
});

