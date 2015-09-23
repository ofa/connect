var isogroup;
$(function() {


    if (tourMode) {
        isogroup = new Isogroup('.group-container', {
            transformsEnabled: false
        });
    } else {
        isogroup = new Isogroup('.group-container');
    }

    var filterIso = function(list) {
        isogroup.filter(list);
        ga('send', 'event', 'Groups Action', 'Filter Groups', list);
    }

    filter = new Filter('.categories-group', categoryList, filterIso);

    $.each(categoryList, function(i, category) {
        var count = isogroup.$el.find('.' + category).length;
        $('.' + category + ' .count').html("(" + count + ")");
    });

    $('.leave-group').click(function() {
        $(this).find('.current').hide();
    });

    $('.layout').click(function(){
        var layout = $(this).data('layout');
        $('.layout').not('[data-layout='+layout+']').removeClass('active');
        $(this).addClass('active');
        
        $('body').removeClass('cards list').addClass(layout);
        isogroup.$el.isotope();
    });
    
    // Start with grid
    
    $('body').addClass('cards');

});