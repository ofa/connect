module.exports = {
    all: {
        //path to input template
        src: "<%= _hogan %>**/*.hogan",
        //output path, relative to Gruntfile.js
        dest: "<%= _minJS %>templates.min.js",
        options: {
            binderName: "hulk"
        }
    }
};