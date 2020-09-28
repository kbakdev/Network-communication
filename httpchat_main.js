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