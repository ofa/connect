module.exports = {
    options: {
        // report: "min",
        drop_console: true
    },
    base: { // Base Module -- used globally
        src: ["<%= _bower %>jquery/dist/jquery.js",
            "<%= _bower %>bootstrap/js/transition.js",
            "<%= _bower %>bootstrap/js/collapse.js",
            "<%= _bower %>bootstrap/js/dropdown.js",
            "<%= _bower %>bootstrap/js/modal.js",
            "<%= _bower %>jasny-bootstrap/js/transition.js",
            "<%= _bower %>jasny-bootstrap/js/fileinput.js",
            "<%= _bower %>jasny-bootstrap/js/offcanvas.js",
            "<%= _bower %>bootbox/bootbox.js",
            "<%= _bower %>magnific-popup/dist/jquery.magnific-popup.js",
            "<%= _vend %>jquery.oembed.secure.js",
            "<%= _vend %>redactor/redactor.js",
            "<%= _bower %>isotope/jquery.isotope.js",
            "<%= _bower %>momentjs/moment.js",
            "<%= _js %>modules/oembed-plugin.js",
            "<%= _js %>modules/Badge.js",
            "<%= _js %>modules/Connect.js",
            "<%= _js %>modules/Compose.js",
            "<%= _js %>modules/Isogroup.js",
            "<%= _js %>modules/Filter.js",
            "<%= _js %>modules/join-leave.js",
            "<%= _js %>modules/dropbox-saver.js",
            "<%= _js %>modules/analytics.js"
        ],
        dest: "<%= _minJS %>base.min.js"
    },
    //Individual pages:
    inbox: {
        src: [
            "<%= _bower %>underscore/underscore.js",
            "<%= _bower %>backbone/backbone.js",
            "<%= _bower %>backbone-deep-model/distribution/deep-model.js",
            "<%= _vend %>marionette-bundle.js",
            "<%= _bower %>hogan/lib/template.js",
            "<%= _minJS %>templates.min.js",
            "<%= _js %>inbox/Inbox.js",
            "<%= _js %>inbox/Inbox.Base.js",
            "<%= _js %>inbox/Inbox.State.js",
            "<%= _js %>inbox/Inbox.Threads.js",
            "<%= _js %>inbox/Inbox.Messages.js",
            "<%= _js %>inbox/Inbox.Controller.js"
        ],
        dest: "<%= _minJS %>inbox.min.js"
    },
    groups: {
        src: ["<%= _js %>sections/groups.js"],
        dest: "<%= _minJS %>groups.min.js"
    },
    resources: {
        src: ["<%= _js %>sections/resources.js"],
        dest: "<%= _minJS %>resources.min.js"
    },
    groupDetail: {
        src: ["<%= _js %>sections/group-detail.js"],
        dest: "<%= _minJS %>group-detail.min.js"
    },
    gallery: {
        src: ["<%= _js %>sections/gallery.js"],
        dest: "<%= _minJS %>gallery.min.js"
    },
    profile: {
        src: ["<%= _js %>sections/profile.js"],
        dest: "<%= _minJS %>profile.min.js"
    },
    newgroup: {
        src: ["<%= _js %>modules/Spinner.js",
            "<%= _js %>modules/Map.js",
        ],
        dest: "<%= _minJS %>newgroup.min.js"
    }
};