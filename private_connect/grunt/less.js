//Here's an example of a customize LESS task -- this compiles the files using the private_connect.less / private_config.less setup, rather than the default.

module.exports = {
    development: {
        options: {
            paths: "<%= _lessPaths %>",
            cleancss: false,
            dumpLineNumbers: "comments"
        },
        files: {
            "<%= _css %>main.css": "<%= _privateless %>private_connect.less",
        }
    },
    production: {
        options: {
            paths: "<%= _lessPaths %>",
            cleancss: true
        },
        files: {
            "<%= _css %>main.min.css": "<%= _privateless %>private_connect.less",
        }
    }
};
