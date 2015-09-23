/*global Backbone */
Inbox.module("Threads", function(Threads, Inbox, Backbone, Marionette, $, _, CONNECT) {
    "use strict";
    var Base = Inbox.Base;

    //Decorate app state for presentation and rendering
    var Modifiers = Backbone.DeepModel.extend({
        defaults: {
            groups_to_mod: "",
            messages_to_mod: "",
            total_threads: "",
            page_number: "",
            total_pages: "",
            has_other_pages: "",
            archive: false,
            unselect: false,
            numSelected: "",
            allMode: false,
            msg_mod_url: CONNECT.services.mod_msg,
            group_mod_url: CONNECT.services.mod_groups,
            area: "Inbox"
        },
        initialize: function(p, o) {
            this.collection = o.collection;
            this.listenTo(this, "change:groups_to_mod change:messages_to_mod change:has_other_pages change:page_number change:total_pages change:total_threads", this.update);
            this.listenTo(this.collection.state, "change", this.update);
            this.listenTo(this.collection, "changeActive", this.update);
        },
        update: function(options) {
            options = options || {};
            var pgAmt = 20,
                pgNum = this.get("page_number"),
                total = this.get("total_threads"),
                end = (pgNum * pgAmt) > total ? total : pgNum * pgAmt,
                start = total === 0 ? 0 : pgNum > 1 ? (pgNum - 1) * pgAmt : 1,
                area = this.collection.state.get("threadArea.name"),
                unselect,
                numSelected,
                allMode;

            if (!!this.collection.getActive().length) {
                unselect = this.collection.getActive().length === this.collection.length;
                allMode = options.allMode || this.collection.getActive().length === total;
                numSelected = options.numSelected ? options.numSelected : this.collection.getActive().length;
            }

            return this.set({
                end: end,
                start: start,
                prev: start > 1,
                next: total > end,
                area: area,
                archive: area === "Archive",
                unselect: unselect,
                numSelected: numSelected,
                allMode: allMode
            });
        }
    });

    Threads.Modifiers = Modifiers;

    Threads.Thread = Base.Model.extend({
        decorate: function() {
            if (!this.get("userthread_status")) return;
            this.set({
                subject: this.get("subject").length < 40 ? this.get("subject") : this.get("subject").slice(0, 40) + "...",
                dateFormatted: moment(this.get("latest_message_at")).format("MMM Do")
            }).setArchived();
        },
        setArchived: function() {
            this.set({
                archived: this.get("userthread_status") === "archived",
            });
        }
    });

    Threads.Threads = Base.Collection.extend({
        model: Threads.Thread,
        initialize: function(m, o) {
            this.controller = o.controller;
            this.multi = true;
            this.init = true;
            this.urlString = "";
            this.state = o.state;
            CONNECT.badge.ready.then(function(badge) {
                this.badge = badge;
            }.bind(this));
            this.modifiers = new Modifiers({
                archive: this.state.get("threadArea.name") === "Archive"
            }, {
                collection: this
            });
            this.listenTo(this.state, "change", _.debounce(this.update, 180).bind(this));
            this.update();
        },
        parse: function(data) {
            var options = _.extend(data.alerts, data.paginator);
            this.modifiers.set(options);
            return data.threads;
        },
        badgeCheck: function() {
            this.badge.$el.off("updated");
            if (this.state.get("threadArea.name") === "Inbox") {
                this.badge.$el.on("updated", function() {
                    this.fetch();
                }.bind(this));
            }
        },
        setTitleText: function() {
            var groupText = !!this.state.get("group.query") ? this.state.groups.get(this.state.get("group.id")).get("name") : "",
                areaText = this.state.get("threadArea.name"),
                text = !!groupText ? groupText + " in " + areaText : areaText;
            this.trigger("changeTitle", text);
        },
        update: function(type) {
            this.deactivate();
            this.setTitleText();
            if (this.badge) this.badgeCheck();
            if (!this.init) this.controller.router.navigate(this.state.get("route"));
            this.urlString = this.state.get("threadArea.query") + this.state.get("group.query") + this.state.get("page.query");
            this.fetch();
            this.init = false;
        },
        url: function() {
            return CONNECT.services.threads + this.urlString;
        }
    });
    //MODEL VIEWS
    var EmptyView = Marionette.ItemView.extend({
        template: "empty",
        tagName: "div",
        initialize: function(o) {
            this.model.set({
                header: o.header,
                subhead: o.subhead,
            });
        }
    });

    var ThreadPreview = Base.ModelView.extend({
        template: "threadPreview",
        tagName: "div",
        className: "thread-item",
        ui: {
            toggle: "label"
        },
        events: {
            "click": "showDetail",
            "click @ui.toggle": "changeActive"
        },
        onBeforeRender: function() {
            this.model.decorate();
            var read = !this.model.get("read") ? " not-read" : "",
                category = this.model.get("is_system_thread") ? "system" : this.model.get("category") ? this.model.get("category") : "personal";

            this.$el.attr("class", "thread-item item " + category + read);
        },
        showDetail: function(e) {
            e.preventDefault();
            if (e.target.tagName == "LABEL" || e.target.tagName == "INPUT") return;
            this.model.set({
                read: true
            });
            if (this.model.get("unread_messages")) this.model.collection.badge.markRead(this.model.get("unread_messages"));
            var id = this.model.get("id"),
                unread = !this.model.get("read");
            this.model.collection.trigger("showDetail", id, unread);
            return this;
        }
    });

    Threads.ThreadPreview = ThreadPreview;

    //COLLECTION VIEW
    Threads.ThreadPreviewList = Marionette.CompositeView.extend({
        ui: {
            actions: "#threadActions",
            compose: ".compose",
            paginator_next: ".pg-next",
            paginator_prev: ".pg-prev",
            allMode: ".all-mode",
            tourButton: ".take-tour"
        },
        events: {
            "click @ui.paginator_next": "nextPage",
            "click @ui.paginator_prev": "prevPage",
            "click @ui.allMode": "changeMode",
            "click @ui.tourButton": "takeTour"
        },
        template: "threadlist",
        childView: ThreadPreview,
        childViewContainer: "#threadlist",
        emptyView: EmptyView,
        emptyViewOptions: {
            header: "INBOX ZERO",
            subhead: "Nice job!"
        },
        initialize: function() {
            this.model = this.collection.modifiers;
            this.listenTo(this.model, "change", this.render);
            this.listenTo(this.collection.state, "change", this.emptyStates);
        },
        onBeforeRender: function() {
            this.scrollTop = $(this.childViewContainer).scrollTop();

        },
        onRender: function() {
            //Bind the dropdown menu actions
            this.ui.actions.on("change", function(e) {
                this[$(e.target).val()].call(this, this.model.get("allMode"));
            }.bind(this));

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

            this.resize();

            $(window)
                .off("resize.childview")
                .on("resize.childview", function() {
                    _.debounce(this.resize(), 200);
                }.bind(this));

            if (this.model.changedAttributes().page_number) {
                this.scrollTop = 0;
                return
            }

            $(this.childViewContainer).scrollTop(this.scrollTop);
        },
        takeTour: function(e) {
            e.preventDefault();
            $.post(CONNECT.services.tour, {
                csrfmiddlewaretoken: $("[name=csrfmiddlewaretoken]").val()
            }, "json").done(function(data) {
                this.ui.tourButton.off();
                document.location = CONNECT.services.explore;
            }.bind(this));
        },
        resize: function() {
            this.$el.find(this.childViewContainer).css({
                height: Math.ceil(0.59 * $(window).height())
            });
        },
        emptyStates: function() {
            var lazyRender = _.debounce(this.render, 300).bind(this),
                groupid = this.collection.state.get("group.id"),
                opts;
            if (groupid !== "") {
                var groups = this.collection.state.groups;

                this.emptyViewOptions = {
                    header: "No messages",
                    subhead: "No messages are in this area for the group \"" + groups.get(groupid).get("name") + "\". Choose a different group, or a different message area."
                }
                lazyRender();
                return;
            }
            switch (this.collection.state.get("threadArea.name")) {
                case "Unread":
                    opts = {
                        header: "No unread messages",
                        subhead: "Good work!"
                    };
                    break;
                case "Archive":
                    opts = {
                        header: "No archived messages",
                        subhead: "Use the archive options in the inbox."
                    };
                    break;
                default:
                    opts = {
                        header: "INBOX ZERO",
                        subhead: "Nice job!"
                    }
            }
            this.emptyViewOptions = opts;
            lazyRender();
        },
        nextPage: function(e) {
            e.preventDefault();
            this.scrollTop = 0;
            this.collection.state.updatePage(1);
        },
        prevPage: function(e) {
            e.preventDefault();
            this.scrollTop = 0;
            this.collection.state.updatePage(-1);
        },
        selectAll: function() {
            this.collection.setAll({
                active: true
            }).trigger("changeActive");
            this.resetActions();
        },
        unselectAll: function() {
            this.collection.setAll({
                active: false
            }).trigger("changeActive");
            this.resetActions();
        },
        activeIDs: function() {
            return _.pluck(this.collection.getActive(), "id").join();
        },
        markReadSelected: function(allMode) {
            this.modSelected(allMode, {
                read: true
            });
        },
        archiveSelected: function(allMode) {
            this.modSelected(allMode, {
                status: "archived"
            });
            this.collection.deactivate().trigger("changeActive");
        },
        modSelected: function(allMode, obj) {
            this.resetActions();
            if (!this.collection.getActive()) return;
            if (allMode) return this.modAll(obj);
            var ids = this.activeIDs();
            this.collection.trigger("post", CONNECT.services.threads + "?id=" + ids, obj, function() {
                this.collection.fetch();
            }, this);
        },
        modAll: function(obj) {
            var callback;
            if (!!obj.read) {
                this.collection.badge.markRead(this.model.get("total_threads"));
                callback = function() {
                    this.collection.setAll({
                        read: true
                    });
                };
            } else {
                this.collection.deactivate();
                this.collection.trigger("changeActive");
                callback = function() {
                    this.collection.reset();
                };
            }
            this.collection.trigger("post", CONNECT.services.threads + this.collection.state.get("threadArea.query"), obj, callback, this);
        },
        resetActions: function() {
            this.ui.actions.val("");
        },
        changeMode: function(e) {
            e.preventDefault();
            this.model.update({
                allMode: true,
                numSelected: this.model.get("total_threads")
            });
        }
    });


}, window.CONNECT);
