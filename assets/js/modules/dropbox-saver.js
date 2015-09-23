// Check to see if Google Analytics is instantiated; if not, create object with an empty array.
// This is intentionally global.
window.ga = window.ga || function() {
    ( window.ga.q =  window.ga.q || []).push(arguments);
};

$(function(){
    var $saveDB = $('.save-db'),
        $checkboxes = $('.styled-checkbox input'),
        $dbElements = $('.styled-checkbox, .db-actions, .cancel');


    $saveDB.click(function(){
        $checkboxes.prop('checked', false);
        $dbElements.show();
        $saveDB.hide();
        ga('send', 'event', 'Dropbox Saver', 'Show');
    });

    $('.cancel').click(function(){
        $dbElements.hide();
        $saveDB.show();
        ga('send', 'event', 'Dropbox Saver', 'Cancel (Local)');
    });

    $('.select-all').click(function(){
        $('.styled-checkbox input').prop('checked', true);
        ga('send', 'event', 'Dropbox Saver', 'Select All');
    });

    $('.select-none').click(function(){
        $('.styled-checkbox input').prop('checked', false);
        ga('send', 'event', 'Dropbox Saver', 'Select None');
    });

    $('.saver-init').click(function(){
        // Dropbox Saver 
        var prefix = window.location.origin,
        list = [];
        
        if ($('.gallery-container :checked').length){
            $('.gallery-container :checked').each(function(){
                var url = $(this).attr('data-img-url'),
                    filename = $(this).attr('data-img-name'),
                    chkdImg = {'url':prefix+url, 'filename':filename};
                list.push(chkdImg);
            });
            var options = {
                files: list,
                cancel: function() {
                    ga('send', 'event', 'Dropbox Saver', 'Cancel (Remote)', '', list.length);
                },
                success: function () {
                    ga('send', 'event', 'Dropbox Saver', 'Success', '', list.length);
                },
                error: function(errmsg) {
                    window.alert("Your images were not saved to Drobox for the following reason: "+errmsg);
                    ga('send', 'event', 'Dropbox Saver', 'Error', 'Remote: ' + errmsg, list.length);
                }
            };
            Dropbox.save(options);
            ga('send', 'event', 'Dropbox Saver', 'Open Dropbox Window', '', list.length);
        } else {
            window.alert('Please select at least one image.');
            ga('send', 'event', 'Dropbox Saver', 'Error', 'Local: No Image(s) Selected');
        }
    });
});