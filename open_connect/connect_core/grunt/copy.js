module.exports = {
    main: {
        files: [{
            expand: true,
            cwd: "<%= _bower %>bootstrap/fonts/",
            src: ["*.*"],
            dest: "<%= _dist %>fonts/"
        }]
    }
};
