// Function to run after page load.
$(function() {
    // Plug in a function that sends text to chat-input and set focus to the text field.
    $('#chat-input')
    .focus()
    .keypress(function(ev) {
    if (ev.which != 13) { // ENTER key.
        return;
    }
    ev.preventDefault();

    // Download content and clear the text box.
    var text = $(this).val();
    $(this).val('');

    // Send the text to the server.
    var text_json = JSON.stringify({
        "text": text
    });
    $.ajax({
        url: '/chat',
        type: 'POST',
        data: text_json,
        async: true
    });
});

// Regularly poll the server for new messages.
var last_message_id = -1;
var chat = $("chat-text");
function checkForNewMessages() {
    var request_json = JSON.stringify({
        "last_message_id": last_message_id
    });

    $.ajax({
        url: '/messages',
        type: 'POST',
        data: request_json,
        dataType: 'json',
        async: true,
        error: function(jqXHR, textStatus, errorThrown) {
            console.log("Failed to fetch new messages: " + errorThrown);

            // Call the function again in a second.
            window.setTimeout(checkForNewMessages, 1000);
        },
    success: function(data) {
        last_message_id = data["last_message_id"];
        data["messages"].forEach(function(cv, idx, arr) {
            var person = cv[0];
            var text = cv[1];
            var chat_line = $('<p/>');
            $('<span/>', {
                text: text
            }).addClass("text").appendTo(chat_line);
            chat_line.appendTo(chat)
        });

        chat.animate({ scrollTop: chat[0].scrollHeight }, 500);
                // Call the function again in a second.
                window.setTimeout(checkForNewMessages, 1000);
            },
        });
    }
    checkForNewMessages();
});