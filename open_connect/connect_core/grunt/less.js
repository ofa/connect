module.exports = {
    development: {
        options: {
            paths: "<%= _lessPaths %>",
            cleancss: false,
            dumpLineNumbers: "comments"
        },
        files: {
            "<%= _css %>main.css": "<%= _less %>connect.less"
            // "<%= _css %>oldie.css": "<%= _less %>oldie.less"
        }
    },
    production: {
        options: {
            paths: "<%= _lessPaths %>",
            cleancss: true
        },
        files: {
            "<%= _css %>main.min.css": "<%= _less %>connect.less"
            // "<%= _css %>oldie.min.css": "<%= _less %>oldie.less"
        }
    }
};
