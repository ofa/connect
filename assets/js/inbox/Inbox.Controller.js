/*global Backbone */

Inbox.module("Controller", function(Controller, Inbox, Backbone, Marionette, $, _) {
    "use strict";

    var Threads = Inbox.Threads,
        Messages = Inbox.Messages,
        State = Inbox.State;

    Controller.Router = Marionette.AppRouter.extend({
            routes: {
                "": "redir",
                "inbox(/)(group/:id/)": "inbox",
                "unread(/)(group/:id/)": "unread",
                "archive(/)(group/:id/)": "archive",
                "id/:id(/)": "showDetail",
                "mod/:thread/msg/:msg(/)": "moderate"
            },
            initialize: function(o) {
                this.controller = o.controller;
            },
            redir: function() {
                this.navigate("inbox/", {
                    trigger: true
                });
            },
            inbox: function(id) {
                this.changeArea("Inbox", id);
            },
            unread: function(id) {
                this.changeArea("Unread", id);
            },
            archive: function(id) {
                this.changeArea("Archive", id);
            },
            changeArea: function(area, id) {
                
                if (Backbone.history.root+this.controller.threads.state.get("route") === window.location.pathname){
                    this.controller.hideDetail();
                    return;
                }
                if (area) {
                    var areaModel = this.controller.threadAreas.findWhere({
                        name: area
                    });
                    this.controller.threadAreas.changeActive(areaModel);
                }
                var current = this.controller.threads.state.get("group.id");
                if (!id) this.controller.groups.deactivate();
                if (id) {
                    var idModel = this.controller.groups.findWhere({
                        id: parseInt(id)
                    });
                    this.controller.groups.changeActive(idModel);
                }
            },
            showDetail: function(id) {
                this.controller.showDetail(id);
            },
            moderate: function(thread, msg) {
                this.controller.moderate(thread, msg);
            }
        });
    Controller.Controller = Marionette.Controller.extend({
            initialize: function() {
                this.csrf = $("[name=csrfmiddlewaretoken]").val();
                this.threadAreas = new State.ThreadAreas([{
                    name: "Inbox",
                    query: "?status=active",
                    active: true
                }, {
                    name: "Unread",
                    query: "?read=false",
                    active: false
                }, {
                    name: "Archive",
                    query: "?status=archived",
                    active: false
                }]);
                this.groups = new State.Groups(CONNECT.user.groups);
                this.threads = new Threads.Threads(false, {
                    controller: this,
                    state: new State.State({
                        groups: this.groups,
                        threadAreas: this.threadAreas
                    })
                });
                this.store = new Backbone.Collection();
                this.modStore = new Backbone.Collection();
            },
            start: function() {
                var areas = new State.ThreadAreasView({
                    collection: this.threadAreas
                });
                var groups = new State.GroupsView({
                    collection: this.groups
                });

                Inbox.threadlist.show(new Threads.ThreadPreviewList({
                    collection: this.threads
                }));

                this.listenTo(this.threads, "showDetail", this.showDetail);
                this.listenTo(this.threads, "post", this.post);
                this.listenTo(this.threads, "mod", this.moderate);
                this.listenTo(this.threads, "changeTitle", this.changeTitle);

                this.areasView = new State.ThreadAreasView({
                    collection: this.threadAreas
                });

                this.groupView = new State.GroupsView({
                    collection: this.groups
                });

                this.setViews(mobileChange());

                $(window).on("mobileSwitch", function(e, mobile) {
                    this.setViews(mobile);
                }.bind(this));
            },
            changeTitle: function (text) {
                document.title = ("Connect | "+text);
            },
            setViews: function(mobile) {
                var areas, groups, oldAreas, oldGroups;
                if (mobile) {
                    areas = "areasMobile";
                    oldGroups = "groups";
                    oldAreas = "areas";
                    groups = "groupsMobile";
                } else {
                    areas = "areas";
                    oldGroups = "groupsMobile";
                    oldAreas = "areasMobile";
                    groups = "groups";
                }

                if (Inbox[oldAreas].hasView()) Inbox[oldAreas].empty({
                    preventDestroy: true
                });
                if (Inbox[oldGroups].hasView()) Inbox[oldGroups].empty({
                    preventDestroy: true
                });

                Inbox[areas].show(this.areasView);
                Inbox[groups].show(this.groupView);
            },
            moderate: function(id, msg) {
                $("body").addClass("detail");
                this.router.navigate("mod/" + id + "/msg/" + msg + "/");

                var cached = this.modStore.get({
                        id: id
                    }),
                    current;
                if (!cached) {
                    current = new Backbone.DeepModel({
                        id: id,
                        messages: new Messages.Mod(false, {
                            id: id,
                            url: "/messages/" + id + "/json/",
                            mod: msg
                        })
                    });
                    this.modStore.add(current);
                } else {
                    current = cached;
                }

                this.msgView = new Messages.ModView({
                    collection: current.get("messages")
                });

                Inbox.threaddetail.show(this.msgView);
                Inbox.threaddetail.$el.removeClass("hidden");

            },
            showDetail: function(id, unread) {
                this.router.navigate("id/" + id + "/");
                $("body").addClass("detail");

                var cached = this.store.get({
                        id: id
                    }),
                    current;
                if (unread || !cached) {
                    current = new Backbone.DeepModel({
                        id: id,
                        messages: new Messages.Messages(false, {
                            id: id,
                            url: "/messages/" + id + "/json/"
                        })
                    });
                    this.store.add(current);
                } else {
                    current = cached;
                }
                this.msgView = new Messages.MessagesView({
                    collection: current.get("messages"),
                    cached: !!cached
                });

                this.listenTo(this.msgView, "changeTitle", this.changeTitle);
                this.listenTo(this.msgView, "post", this.post);
                this.listenTo(this.msgView, "back", this.back);

                Inbox.threaddetail.show(this.msgView);
                Inbox.threaddetail.$el.removeClass("hidden");

            },
            hideDetail: function() {
                $("body").removeClass("detail");
                if (Inbox.threaddetail.hasView()) {
                    this.stopListening(this.msgView);
                    Inbox.threaddetail.$el.addClass("hidden");
                    Inbox.threaddetail.reset();
                }
            },
            back: function() {
                this.hideDetail();
                this.router.navigate(this.threads.state.get("route"));
            },
            post: function(url, settings, callback, context) {
                var postSettings = $.extend(settings, {
                        csrfmiddlewaretoken: this.csrf
                    });

                    $.post(url, postSettings).done(function() {
                        //Post callbacks are run with Controller as "this" unless a context is passed
                        if (!callback) return;
                        if (context) return callback.call(context);
                        callback.call(this);
                    }.bind(this));
            }
        });


    Inbox.on("start", function() {
        var controller = new Controller.Controller();

        controller.router = new Controller.Router({
            controller: controller
        });

        controller.start();

        Backbone.history.start({
            pushState: true,
            root: "/messages/"
        });
    });
});
