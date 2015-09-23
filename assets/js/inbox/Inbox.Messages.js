Inbox.module("Messages", function(Messages, Inbox, Backbone, Marionette, $, _, CONNECT, bootbox, twttr) {
        var Message = Inbox.Base.Model.extend({
            initialize: function() {
                var date = this.get("sent_at");
                this.set({
                    active: !this.get("read"),
                    date: moment(date).calendar()
                });
            },
            setScrunch: function() {
                if (this.get("scrunchToggle") || this.get("active")) return;
                this.set({
                    "scrunched": true
                });
            }
        });

        Messages.Message = Message;

        Messages.Messages = Inbox.Base.Collection.extend({
            model: Message,
            initialize: function(m, o) {
                this.id = o.id;
                this.url = o.url;
                this.multi = true;
                this.fetch().done(function() {
                    this.afterFetch();
                }.bind(this));
                this.thread = new Inbox.Threads.Thread();
            },
            comparator: "sent_at",
            parse: function(data) {
                this.thread.set(data.thread);
                return data.connectmessages;
            },
            afterFetch: function() {
                this.cached = true;
                this.last().set({
                    active: true
                });
                this.read = this.where({
                    read: true
                });
                if (this.read.length > 5) {
                    this.scrunch();
                }
                this.trigger("fetchComplete");
            },
            scrunch: function() {
                this.read[0].set({
                    "scrunchToggle": true,
                    "scrunchLength": this.read.length - 1
                });

                _.each(this.read, function(model) {
                    model.setScrunch();
                });
            },
            unscrunch: function() {
                this.setAll({
                    "scrunchToggle": false,
                    "scrunched": false
                });
            },
        });

        Messages.Mod = Messages.Messages.extend({
            initialize: function(m, o) {
                this.id = o.id;
                this.url = o.url;
                this.multi = true;
                this.fetch().done(function() {
                    this.afterFetch(o.mod);
                }.bind(this));
                this.thread = new Inbox.Threads.Thread();
            },
            afterFetch: function(msg) {
                this.thread.set({
                    mod: this.get(msg).attributes
                });
                this.setAll({
                    active: false
                });
            }
        });

        var MessageView = Inbox.Base.ModelView.extend({
            template: "message",
            tagName: "div",
            ui: {
                "toggle": ".accordion-toggle",
                "flag": ".flag"
            },
            className: "panel panel-default",
            events: {
                "click @ui.toggle": "changeActive",
                "click @ui.flag": "flagPrompt"
            },
            onRender: function() {
                this.linkBlanker();
                if (this.model.get("scrunched")) {
                    this.$el.attr("class", "");
                } else {
                    this.$el.attr("class", this.className);
                }
            },
            linkBlanker: function() {
                // Find all non-relative not-internal/local links, set target="_blank"
                this.$el.find(".msg-text a")
                    .not("[href*='" + window.location.host + "']")
                    .not("[href^='/']").each(
                        function() {
                            $(this).attr("target", "_blank");
                        });
            },
            flagPrompt: function(e) {
                e.preventDefault();
                var url = this.ui.flag.attr("href");
                var group = this.ui.flag.attr("data-group");

                bootbox.confirm("Are you sure you want to flag this message for inappropriate content?", function(result) {
                    if (result) this.model.collection.trigger("flag", this.model, url, group);
                }.bind(this));
            }
        });
    
        Messages.MessageView = MessageView;

        Messages.MessagesView = Marionette.CompositeView.extend({
            template: "threadMessages",
            childView: MessageView,
            childViewContainer: "#msg-list",
            className: "container thread-messages",
            ui: {
                "reply": ".reply",
                "archive": ".archive",
                "compose": ".compose",
                "back": ".back-to-inbox",
                "expand": ".expand-all",
                "collapse": ".collapse-all",
                "scrunchToggle": ".scrunch-toggle"
            },
            events: {
                "click @ui.archive": "archive",
                "click @ui.back": "back",
                "click @ui.expand": "expandAll",
                "click @ui.collapse": "collapseAll",
                "click @ui.scrunchToggle": "unscrunch"
            },
            childEvents: {
                "render": "oembed"
            },
            initialize: function(o) {
                this.model = this.collection.thread;
                this.listenTo(this.model, "change", this.render);
                this.listenTo(this.collection, "flag", this.flag);
                if (!this.collection.cached) {
                    this.listenTo(this.collection, "fetchComplete", function() {
                        this.oembed();
                    }.bind(this));
                }
            },
            onBeforeRender: function() {
                this.model.setArchived();
            },
            onRender: function() {
                this.bindReply();
                if (this.collection.cached) {
                    this.oembed();
                }
            },
            oembed: function() {
                var that = this;
                this.$el.find(".msg-content a").not(".done").each(function() {
                    //Blank text links for backwards compatibility; remove in 60 days
                    if ($(this).html() === "" || $(this).attr("data-embed") === "true") {
                        $(this).oembed(null, {
                            includeHandle: false,
                            afterEmbed: function() {
                                $(this).addClass("done");
                            }
                        });
                        that.refreshEmbeds();
                    }
                });
            },
            refreshEmbeds: function () {
                 var time = setTimeout(function(){
                    twttr.widgets.load();
                    instgrm.Embeds.process();
                    $("a[data-flickr-embed]").remove();
                 }, 500);
            },
            collapseAll: function(e) {
                e.preventDefault();
                this.collection.deactivate();
            },
            expandAll: function(e) {
                e.preventDefault();
                this.collection.setAll({
                    active: true,
                    scrunched: false,
                    scrunchToggle: false
                });
            },
            bindReply: function() {

                if (CONNECT.mobile) return;
                var reply = new Compose(this.ui.reply);

                reply.$el.on("compose.shown", function() {
                    ga("send", "event", "Compose Action", "New message", reply.messageType + ", " + reply.to);
                });

                reply.$el.on("compose.sent", function(e, type, to) {
                    ga("send", "event", "Compose Action", "Message sent", type + ", " + to);
                });

                //Bind compose
                this.ui.compose.attr("href", CONNECT.services.compose);

                var compose = new Compose(this.$el.find(".compose"));

                //Google analytics tracking on compose
                compose.$el.on("compose.sent", function(e, type, to) {
                    ga("send", "event", "Compose Action", "Message sent", type + ", " + to);
                });

                compose.$el.on("compose.shown", function() {
                    ga("send", "event", "Compose Action", "New message", "New message");
                });
            },
            back: function(e) {
                if (e) e.preventDefault();
                this.trigger("back");
            },
            archive: function(e) {
                e.preventDefault();
                var id = this.model.get("id");

                this.trigger("post", CONNECT.services.threads + "?id=" + id, {
                    status: "archived"
                }, function() {
                    this.back();
                    this.threads.remove(id);
                });
            },
            unscrunch: function() {
                this.collection.unscrunch();
            },
            flag: function(model, url, group) {
                this.trigger("post", url, "", (function() {
                    this.collection.remove(model);
                    if (!this.collection.length) this.trigger("back")
                }), this);
                ga("send", "event", "Inbox Action", "Flag", group);
            }
        });

        Messages.ModView = Messages.MessagesView.extend({
            template: "moderation"
        });

    },
    window.CONNECT,
    bootbox,
    twttr);
