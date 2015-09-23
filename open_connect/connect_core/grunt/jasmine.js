module.exports = {
    main: {
        src: [
            "<%= _js %>modules/Badge.js",
            "<%= _js %>inbox/Inbox.js",
            "<%= _js %>inbox/Inbox.Base.js",
            "<%= _js %>inbox/Inbox.State.js",
            "<%= _js %>inbox/Inbox.Threads.js",
            "<%= _js %>inbox/Inbox.Messages.js",
            "<%= _js %>inbox/Inbox.Controller.js" 
        ],
        options: {
            specs: "<%= _js %>**/*Spec.js",
            vendor: [
                "<%= _vend %>sinon-1.15.0.js",
                "<%= _bower %>jquery/dist/jquery.js",
                "<%= _bower %>underscore/underscore.js",
                "<%= _bower %>backbone/backbone.js",
                "<%= _bower %>backbone-deep-model/distribution/deep-model.js",
                "<%= _bower %>momentjs/moment.js",
                "<%= _vend %>marionette-bundle.js",
                "<%= _vend %>redactor/redactor.js",
                "<%= _js %>modules/oembed-plugin.js",
                "<%= _bower %>hogan/lib/template.js",
                "<%= _bower %>bootstrap/dist/js/bootstrap.js",
                "<%= _bower %>bootbox/bootbox.js",
                "<%= _minJS %>templates.min.js",
                "<%= _js %>modules/Compose.js",
                "https://platform.twitter.com/widgets.js",
                "https://platform.instagram.com/en_US/embeds.js"
            ],
            keepRunner: true,
            helpers: ["<%= _js %>**/*Helper.js"]
        }
    }
};
