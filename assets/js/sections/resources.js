var isogroup;
$(function() {
    isogroup = new Isogroup('.resources-container');

    var filterIso = function(list) {
        isogroup.filter(list);
        ga('send', 'event', 'Resource Action', 'Filter resources', list);
    }

    filter = new Filter('.file-type-group', file_types, filterIso);

    $.each(file_types, function(i, type) {
        var count = isogroup.$el.find('.' + type).length;
        $('.file-type-group .' + type + ' .count').html("(" + count + ")");
    });

    $('.layout').click(function() {
        var layout = $(this).data('layout');
        $('.layout').not('[data-layout=' + layout + ']').removeClass('active');
        $(this).addClass('active');

        if (layout == 'list') {
            isogroup.$el.find('.icon-140').removeClass('icon-140').addClass('.icon-32');
        } else {
            isogroup.$el.find('.icon-32').removeClass('icon-32').addClass('.icon-140');
        }

        $('body').removeClass('cards list').addClass(layout);
        isogroup.$el.isotope();
    });

    $('.delete').click(function(event) {
        event.preventDefault();
        var el = $(this);
        var csrf = $('[name="csrfmiddlewaretoken"]').val();
        console.log(csrf);
        var url = el.attr('href');
        bootbox.dialog({
            message: "Are you sure you want to remove this file?",
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
                            } else {
                                bootbox.alert("We couldn't deleted the selected file. Reason: " + data.error);
                            }
                        });
                    }
                },
                cancel: {
                    label: "Cancel",
                    className: "btn btn-danger btn-remove"
                }
            }
        });
    });

    // Start with grid

    $('body').addClass('cards');

});