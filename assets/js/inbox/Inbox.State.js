/*global Backbone */

Inbox.module("State", function(State, Inbox, Backbone, Marionette, $, _) {
    "use strict";
    var Base = Inbox.Base;

    State.State = Backbone.DeepModel.extend({
        page1: {
            id: 1,
            query: "&page=1"
        },
        defaults: {
            threadArea: {
                name: "Inbox",
                query: "?status=active"
            },
            group: {
                id: "",
                query: ""
            },
            page: {
                id: 1,
                query: "&page=1"
            },
            route: "inbox/"
        },
        initialize: function(options) {
            this.threadAreas = options.threadAreas;
            this.groups = options.groups;

            this.listenTo(this.threadAreas, "changeActive", this.updateThreadArea);

            this.listenTo(this.groups, "changeActive", this.updateGroups);
        },
        makeRoute: function() {
            var areaRoute = this.get("threadArea.name").toLowerCase() + "/";
            var groupRoute = !!this.get("group.id") ? "group/" + this.get("group.id") + "/" : "";
            this.set({
                route: areaRoute + groupRoute
            });
        },
        updateThreadArea: function() {
            this.set({
                threadArea: {
                    name: this.threadAreas.getActive().get("name"),
                    query: this.threadAreas.getActive().get("query")
                },
                page: this.page1
            }).makeRoute();
        },
        updateGroups: function() {
            this.set({
                group: {
                    id: this.groups.getActive() ? this.groups.getActive().get("id") : "",
                    query: this.groups.getActive() ? this.groups.getActive().get("query") : ""
                },
                page: this.page1
            }).makeRoute();
        },
        updatePage: function(amt) {
            var current = this.get("page.id");

            current = current + amt < 1 ? 1 : current + amt;
            this.set({
                page: {
                    id: current,
                    query: "&page=" + current
                }
            });
        }
    });

    //COLLECTIONS

    State.ThreadAreas = Base.Collection.extend({
        model: Base.Model,
        initialize: function() {
            this.disallowNull = true;
        }
    });

    State.Groups = Base.Collection.extend({
        model: Base.Model
    });

    //COLLECTION VIEWS

    State.ThreadAreasView = Marionette.CollectionView.extend({
        tagName: "ul",
        childView: Base.ModelView.extend({
            template: "threadArea"
        })
    });

    State.GroupsView = Marionette.CollectionView.extend({
        tagName: "ul",
        childView: Base.ModelView.extend({
            template: "group"
        })
    });
});
