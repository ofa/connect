$(function() {
    var compose = new Compose('.compose');

    function oembed() {
    	console.log("EMBEDDDD")
        $(".threads a").not('.done').each(function() {
            if ($(this).html() === '' || $(this).attr("data-embed") === "true") {
                $(this).empty().oembed(null, {
                    includeHandle: false,
                    afterEmbed: function() {
                        $(this).addClass('done');
                        var time = setTimeout(function() {
                            twttr.widgets.load();
                            instgrm.Embeds.process();
                            $('a[data-flickr-embed]').remove();
                        }, 800);
                    }
                });
            }
        });

    }

    oembed();

    $('panel-collapse').on('shown.bs.collapse', oembed);
});
