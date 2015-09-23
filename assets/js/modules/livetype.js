function liveType(inputElement, functionName) {
    var timer;

    $(inputElement).on('keydown', function(e) {
        if (e.which == 13) {
            e.preventDefault();
            e.stopPropagation();
        }
    });

    $(inputElement).bind('keyup input', function() {
        clearTimeout(timer);
        timer = setTimeout(functionName, 350);
    });
}