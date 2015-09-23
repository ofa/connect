$(function() {
    var isogroup = new Isogroup('.group-container');

    $('.expand').magnificPopup({
        type: 'image',
        zoom: {
            enabled: true, // By default it's false, so don't forget to enable it
            duration: 300, // duration of the effect, in milliseconds
            easing: 'ease-in-out' // CSS transition easing function
        }
    });

    $('.remove').click(function(event) {
        event.preventDefault();
        var el = $(this);
        var csrf = $('[name="csrfmiddlewaretoken"]').val();
        var url = el.attr('href');
        bootbox.dialog({
            message: "Remove this person from the group?",
            className: "remove-modal",
            onEscape: function () {},
            buttons: {
                remove: {
                    label: "Remove",
                    className: "btn btn-primary btn-remove",
                    callback: function() {
                        $.post(url, {'csrfmiddlewaretoken': csrf}, function(data) {
                            if(data.success) {
                                isogroup.$el.isotope('remove', el.closest('.item')).isotope('reLayout');
                                var count = parseInt($('h1 .count').html());
                                $('h1 .count').html(count - 1);
                            } else {
                                bootbox.alert("We couldn't remove the user you selected from this group. Reason: " + data.error);
                            }
                        });
                    }
                },
                cancel: {
                    label: "Cancel",
                    className: "btn btn-danger btn-remove",
                    callback: function () {
                        bootbox.alert("The user was not removed from this group.");
                    }
                }
            }
        });
    });
});

var compose = new Compose('.compose');

$('.group-select').hide();

$('#'+$('#sub_group_select').val()).show();

$('#sub_group_select').on('change', function(e){
    $('.group-select').hide();
    var val = $(this).val();
    $('#'+val).show();
});
