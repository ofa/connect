
$(function(){
    window.ga = window.ga || function() {
        (window.ga.q = window.ga.q || []).push(arguments);
    };

    // We use mouseDown because it's more likely to be sent to Google before
    // the user moves to the next page. We bind to document and search for .ga
    // elements to allow us to track post-document-ready elements added to the dom
    $(document).on('mousedown.connect.ga', '.ga', function() {
        // Keep everything short and clean, just do everything inside the ga() 'send' call
        var elem = $(this);
        ga('send', {
            'hitType': 'event',
            'eventCategory': elem.attr('data-campaign') || 'Click',
            'eventAction': elem.attr('data-action') || 'Action',
            'eventLabel': elem.attr('data-label') || (elem.attr('href') || ''),
            'eventValue': isNaN(elem.attr('data-value')) ? undefined : parseInt(elem.attr('data-value'), 10),
            'nonInteraction': elem.attr('data-noninteraction') === "1" ? true : false
        });
    });
});
