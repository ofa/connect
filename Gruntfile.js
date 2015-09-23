module.exports = function(grunt) {
    var path = require("path");
    var target = grunt.option("target") || "open_connect/connect_core";
    var dataFile = grunt.file.readJSON("./" + target + "/grunt_config.json");

    require("load-grunt-config")(grunt, {
        // path to task.js files, defaults to grunt dir
        configPath: path.join(process.cwd(), target, "grunt"),
        data: dataFile
    });
};
