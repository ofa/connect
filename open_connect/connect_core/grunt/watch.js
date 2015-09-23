module.exports = {
    css: {
        files: ["<%= _lessPath %>**/*.less", "<%= _bowerPath %>bento-box/*.less"],
        tasks: ["less", "autoprefixer"],
        options: {
            livereload: true,
        },
    },
    // js: {
    //     files: ["<%= _jsPath %>**/*.js"],
    //     tasks: ["dist"],
    //     options: {
    //         livereload: true,
    //     },
    // },
    hogan: {
        files: ["<%= _hoganPath %>**/*.hogan"],
        tasks: ["hogan"]
    },
    jasmine: {
        files: ["./open_connect/connect_core/grunt/jasmine.js","<%= _js %>**/*Spec.js","<%= _jsPath %>**/*.js"],
        tasks: ["jasmine"],
        options: {
            livereload: true,
        }
    }
};
