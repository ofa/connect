// Check to see if Google Analytics is instantiated; if not, create object with an empty array.
// This is intentionally global.
window.ga = window.ga || function() {
    (window.ga.q = window.ga.q || []).push(arguments);
};

if (!RedactorPlugins) var RedactorPlugins = {};



RedactorPlugins.oembed = function() {
    return {
        getTemplate: function() {
            return String() + '<section id="redactor-modal-oembed">' +
                '<p>Paste in a url to embed a photo, video, or other media snippet:</p>' +
                '<input id="oembed-link"></input>' +
                '<p>Use any of the following services embed your content:</p>' +
                '<ul><li>Twitter</li><li>Instagram</li><li>YouTube</li></ul>' +
                '</section>';
        },
        init: function() {
            var button = this.button.add('oembed', 'Embed');

            this.button.addCallback(button, this.oembed.showModal);

            // this.counter = 0;
        },
        showModal: function() {
            this.modal.addTemplate('oembed', this.oembed.getTemplate());

            this.modal.load('oembed', 'Embed Media', 500);

            this.modal.createCancelButton();

            var button = this.modal.createActionButton('Insert');

            button.on('click', this.oembed.insertFromModal);

            this.selection.save();

            this.modal.show();
        },
        insertFromModal: function(html) {

            var link = $('#oembed-link').val(),
                url = '<a href="' + link + '" class="embed" data-embed="true">'+$('#oembed-link').val()+'</a>';

            this.selection.restore();
            this.insert.html(url);

            this.modal.close();

            $("a[data-embed=true]").not('.done').oembed(null, {
                includeHandle: false,
                afterEmbed: function() {
                    $(this).addClass('done');
                }
            });

            ga('send', 'event', 'Compose Action', 'insert oembed', link);
        }
    }
};
