/*global Backbone */
"use strict";

if (!Object.keys) {
    Object.keys = function(obj) {
        var keys = [],
            k;
        for (k in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, k)) {
                keys.push(k);
            }
        }
        return keys;
    };
}

Marionette.Renderer = {
    //Modify renderer to work with Hogan.render
    //change global template var here
    render: function(template, data) {
        $.extend(data,{icon_prefix: window.CONNECT.icon_prefix});
        return window.templates[template].render(data);
    }
};

Backbone.Collection.prototype.setAll = function(options) {
    this.each(function(model) {
        model.set(options);
    });
    return this;
}

window.Inbox = new Backbone.Marionette.Application();

Inbox.addRegions({
    areas: "#areas",
    areasMobile: "#areas-mobile",
    groups: "#groups",
    groupsMobile: "#groups-mobile",
    threadlist: "#threads-container",
    threaddetail: "#thread-detail"
});
