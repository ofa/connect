module.exports = {
    options: {
        browsers: ["last 2 versions", "ie 9"]
    },
    dev: {
        src: "<%= _css%>main.css"
    },
    prod: {
        src: "<%= _css%>main.min.css"
    }
};
