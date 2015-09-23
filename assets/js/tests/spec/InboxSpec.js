describe("Inbox", function() {

    describe("Base classes >", function() {

        /*
        Internal utility classes that makeup the bulk of the inbox-- Base Collection is the foundation,
        and .changeActive() makes changes to which models should be active based on criteria set when in instance of the collection is created, like, should multiple models be allowed to be
        active ("multi") and should a model always be active("disallowNull")?
        */

        var base;

        beforeEach(function() {
            base = Inbox.module("Base");
        });

        describe("Base Model", function() {

            it("should have a toggle method that toggles the 'active' property directly", function() {

                var thing = new base.Model({
                    blah: "thing",
                    active: false
                });

                expect(thing.get("active")).toEqual(false);
                expect(thing.isActive()).toEqual(thing.get("active"));

                thing.toggle();

                expect(thing.get("active")).toEqual(true);
                expect(thing.isActive()).toEqual(thing.get("active"));


            });
        });

        describe("Base Collection", function() {
            it("should allow multiple active models if the collection has multi = true", function() {

                var arr = [{
                        blah: "bear"
                    }, {
                        blah: "cat",
                        active: true
                    }, {
                        blah: "owl"
                    }],
                    multiNull = new base.Collection(arr);

                multiNull.multi = true;

                var activeModel = multiNull.getActive();

                expect(activeModel.length).toEqual(1);
                expect(activeModel[0] instanceof base.Model).toBe(true);
                expect(activeModel[0].get("blah")).toEqual("cat");

                multiNull.changeActive(multiNull.at(0));

                activeModel = multiNull.getActive();

                expect(activeModel.length).toEqual(2);
            });

            it("should allow no models to be active if disallowNull = false", function() {

                var arr = [{
                        blah: "thing1"
                    }, {
                        blah: "thing2",
                        active: true
                    }, {
                        blah: "thing3"
                    }],
                    multiNull = new base.Collection(arr);

                multiNull.multi = true;

                var activeModel = multiNull.getActive();

                //this when multi = true, .getActive() returns an ARRAY

                expect(activeModel[0] instanceof base.Model).toBe(true);

                multiNull.changeActive(activeModel[0]);

                activeModel = multiNull.getActive();

                expect(activeModel.length).toEqual(0);
            });

            it("should allow NOT multiple active or NO active models if the collection does not have multi = true and if disallowNull = true", function() {

                var arr = [{
                        test: "one",
                        active: true
                    }, {
                        test: "two"
                    }, {
                        test: "three"
                    }],
                    singleNoNull = new base.Collection(arr);

                singleNoNull.disallowNull = true;

                //when multi = false, getActive() returns a single model

                expect(singleNoNull.getActive() instanceof base.Model).toBe(true);
                expect(singleNoNull.getActive().get("test")).toEqual("one");

                singleNoNull.changeActive(singleNoNull.getActive());


                expect(singleNoNull.getActive().get("test")).toEqual("one");

                var two = singleNoNull.findWhere({
                    test: "two"
                });

                singleNoNull.changeActive(two);

                expect(singleNoNull.getActive() instanceof base.Model).toBe(true);
                expect(singleNoNull.getActive().get("test")).toEqual("two");
            });

            it("should set all active models to active:false when deactivate is called", function() {
                var arr = [{
                        blah: "bear"
                    }, {
                        blah: "cat",
                        active: true
                    }, {
                        blah: "owl"
                    }],
                    coll = new base.Collection(arr);

                expect(coll.getActive() instanceof base.Model).toBe(true);

                coll.deactivate();

                expect(coll.getActive()).toBeUndefined();


            });
        });
    });

    describe("App Specific Tests > ", function() {
        var base, state, controller, myState;

        beforeAll(function() {
            //One global badge that runs in the background
            var div = $('<div>');
            window.CONNECT = window.CONNECT || {};
            window.CONNECT.badge = new Badge(div, "/badge_endpoint", 4000);

            window.CONNECT.badge.init();
        });

        afterAll(function() {
            clearInterval(window.CONNECT.badge.repeat);
        });

        beforeEach(function() {

            base = Inbox.module("Base");

            $("body").append('<main id="app-test-area"><div id="manager" class="thread-manager"><section id="areas" class="thread-areas"></section><section id="groups" class="thread-filter"></section></div><div id="threads"><div id="threads-container"></div></div><div id="thread-detail" class="thread-detail hidden"></div><nav id="navmenu-left" class="navmenu navmenu-default navmenu-fixed-left offcanvas dark-form" role="navigation"><section id="areas-mobile" class="thread-areas"></section><section id="groups-mobile" class="thread-filter"></section></nav></main>');
            state = Inbox.module("State");
            controller = Inbox.module("Controller");

            myState = new state.State({
                threadAreas: new state.ThreadAreas([{
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
                }]),
                groups: new state.Groups([{
                    name: "Cats Group",
                    shortname: "Cats...",
                    id: 1,
                    query: "&group=1",
                    category: "cats"
                }, {
                    name: "Dogs group",
                    shortname: "Dogs group",
                    id: 2,
                    query: "&group=2",
                    category: "dogs"
                }, {
                    name: "Pizza Group",
                    shortname: "Pizza Group",
                    id: 3,
                    query: "&group=3",
                    category: "pizza"
                }])
            });

        });

        afterEach(function() {
            $("#app-test-area").remove();
        });

        describe("State related classes", function() {

            /*
            State, aka the Thread Manager, aka the left-hand column. Changes to this modify the route,
            which automatically flow to the Thread Preview List view (below)
            */

            describe("State model", function() {
                it("should contruct a route based on the Area and Group", function() {

                    //init Route
                    myState.makeRoute();
                    expect(myState.get("route")).toEqual("inbox/");

                    //directly change the group
                    myState.set("group.id", "4");
                    myState.makeRoute();
                    expect(myState.get("route")).toEqual("inbox/group/4/");

                    //directly change the area
                    myState.set("threadArea.name", "AREA51");
                    myState.makeRoute();
                    expect(myState.get("route")).toEqual("area51/group/4/");
                });

                it("should automatically update the route when the Area or Group is updated", function() {
                    //init Route
                    myState.makeRoute();
                    expect(myState.get("route")).toEqual("inbox/");

                    //Update area via method / listener
                    var unread = myState.threadAreas.findWhere({
                        name: "Unread"
                    });
                    myState.threadAreas.changeActive(unread);

                    expect(myState.get("route")).toEqual("unread/");

                    //Update group via method / listener
                    var dawgs = myState.groups.findWhere({
                        name: "Dogs group"
                    });
                    myState.groups.changeActive(dawgs);

                    expect(myState.get("route")).toEqual("unread/group/2/");

                });
            });
        });

        describe("Thread classes >", function() {

            var threads, threadColl;

            /*
            Threads are groups of Messages, sent either to a Group or a single recipient.
            Also included in this module is "Modifiers," a helper object that takes changes
            from the route and manifests them in changes to the threadlist, such as
            pagination, filtering, etc.*/


            beforeEach(function() {
                threads = Inbox.module("Threads");

                threadsColl = new threads.Threads(false, {
                    controller: {
                        router: {
                            navigate: function() {}
                        }
                    },
                    state: myState
                });

            });

            describe("Modifiers model", function() {
                it("should change the model based on changes state obtained through fetching", function() {

                    var mods = new threads.Modifiers({}, {
                        collection: threadsColl
                    });

                    mods.update();

                    //init state
                    expect(mods.get("start")).toEqual(1);
                    expect(mods.get("next")).toBe(false);
                    expect(mods.get("prev")).toBe(false);
                    expect(mods.get("total_threads")).toBeFalsy();
                    expect(mods.get("groups_to_mod")).toBeFalsy();
                    expect(mods.get("messages_to_mod")).toBeFalsy();
                    expect(mods.get("numSelected")).toBeFalsy();

                    mods.set(threads_json.paginator);

                    expect(mods.get("start")).toEqual(1);
                    expect(mods.get("end")).toEqual(2);
                    expect(mods.get("prev")).toBe(false);
                    expect(mods.get("total_threads")).toEqual(2);

                    mods.set(threads_json.alerts);

                    expect(mods.get("groups_to_mod")).toEqual(0);
                    expect(mods.get("messages_to_mod")).toEqual(15);

                    threadsColl.set(threads_json.threads);

                    var thatOneThread = threadsColl.findWhere({
                        id: 45884
                    });

                    threadsColl.changeActive(thatOneThread);

                    expect(mods.get("numSelected")).toEqual(1);
                });
            });


            describe("Thread model", function() {
                it("should decorate the information in the model to the proper format", function() {
                    var thread = new threads.Thread(threads_json.threads[0]);

                    expect(thread.get("latest_message_at")).toEqual("2015-06-10 19:57:03.732808-05:00");

                    expect(thread.get("subject").length).toBeGreaterThan(40);

                    thread.decorate();

                    expect(thread.get("dateFormatted")).toEqual("Jun 10th");
                    expect(thread.get("subject")).toEqual("Lorem ipsum dolor sit amet, consectetur ...");
                    expect(thread.get("subject").length).toEqual(43);
                });
            });

            describe("Threads collection >", function() {

                it("should have a Modifiers model at the .modifiers property on init", function() {
                    expect(threadsColl.modifiers).toBeTruthy();

                    expect(threadsColl.modifiers instanceof threads.Modifiers).toBe(true);
                });

                it("should contruct a URL based on state, fetch the appropriate messages and update the collection", function() {

                    spyOn(threadsColl, 'fetch');

                    expect(threadsColl.urlString).toEqual("?status=active&page=1");

                    var archive = threadsColl.state.threadAreas.findWhere({
                            name: "Archive"
                        }),
                        group = threadsColl.state.groups.findWhere({
                            name: "Cats Group"
                        });

                    threadsColl.state.threadAreas.changeActive(archive);
                    expect(threadsColl.state.get("threadArea.name")).toEqual("Archive");
                    threadsColl.update();

                    expect(threadsColl.urlString).toEqual("?status=archived&page=1");

                    expect(threadsColl.fetch).toHaveBeenCalled();

                    expect(threadsColl.fetch.calls.count()).toEqual(1);

                    threadsColl.state.updatePage(4);
                    threadsColl.update();

                    //updatePage adds the amount to the current page
                    expect(threadsColl.urlString).toEqual("?status=archived&page=5");

                    threadsColl.state.groups.changeActive(group);
                    threadsColl.update();

                    //When changing groups, page is always reset to '1'
                    expect(threadsColl.urlString).toEqual("?status=archived&group=1&page=1");
                });

                it("should check the badge object passed in when we are in the Inbox, but not otherwise", function() {

                    spyOn(threadsColl, 'fetch');

                    expect(threadsColl.state.get("threadArea.name")).toEqual("Inbox");

                    CONNECT.badge.$el.trigger("updated");

                    expect(threadsColl.fetch).toHaveBeenCalled();

                    expect(threadsColl.fetch.calls.count()).toEqual(1);

                    var archive = threadsColl.state.threadAreas.findWhere({
                        name: "Archive"
                    });

                    threadsColl.state.threadAreas.changeActive(archive);
                    expect(threadsColl.state.get("threadArea.name")).toEqual("Archive");

                    threadsColl.update();
                    threadsColl.fetch.calls.reset();

                    CONNECT.badge.$el.trigger("updated");

                    expect(threadsColl.fetch.calls.count()).toEqual(0);
                });
            });

            describe("Thread Preview view >", function() {

                var thread, threadView;

                beforeEach(function() {
                    thread = new threads.Thread({
                        "latest_message_at": "2015-07-10 19:15:46.028556-05:00",
                        "total_messages": "2",
                        "group": "Climate Change National Group",
                        "read": false,
                        "category": "climate",
                        "is_system_thread": false,
                        "unsubscribe_url": "/messages/45883/unsubscribe/",
                        "reply_url": "/messages/45883/reply/",
                        "snippet": "This message is so cool...",
                        "userthread_status": "active",
                        "unread_messages": 2,
                        "group_url": "/groups/39/",
                        "json_url": "/messages/45883/json/",
                        "group_id": 39,
                        "type": "group",
                        "id": 72637,
                        "subject": "I am unread message"
                    });

                    threadsColl.add(thread);

                    threadView = new threads.ThreadPreview({
                        model: thread
                    });

                    threadView.render();

                    $('#threads').append(threadView.$el);

                    spyOn(threadsColl, 'trigger');
                });

                afterEach(function() {
                    $('#threads').empty();
                });

                it("on click, it should set the corresponsing model to read, and trigger the showDetail event", function() {

                    expect(thread.get('read')).toBe(false);

                    threadView.$el.click();

                    expect(thread.get('read')).toBe(true);
                    expect(threadsColl.trigger).toHaveBeenCalled();
                    expect(threadsColl.trigger).toHaveBeenCalledWith("showDetail", 72637, false);
                });
            });

            describe("Thread Preview List view >", function() {

                var threadlistView;

                beforeEach(function() {

                    threadsColl.reset(more_threads_json.threads);

                    threadlistView = new threads.ThreadPreviewList({
                        collection: threadsColl
                    });

                    threadlistView.render();

                    $("#threads-container").append(threadlistView.$el);

                    $("#threadlist").css({
                        "overflow": "scroll"
                    });
                });

                afterEach(function() {
                    $("#threads-container").empty();
                });

                it("onBeforeRender, it should capture the scroll position", function() {
                    threadlistView.scrollTop = null;

                    expect(threadlistView.scrollTop).toBeFalsy();

                    $("#threadlist").scrollTop(45);

                    threadlistView.onBeforeRender();

                    expect(threadlistView.scrollTop).toBe(45);
                });
                it("should have an empty state that corresponds to the Thread Area or filtered Group", function() {

                    var unread = threadsColl.state.threadAreas.findWhere({
                            name: "Unread"
                        }),
                        archive = threadsColl.state.threadAreas.findWhere({
                            name: "Archive"
                        });

                    threadsColl.reset([]);

                    //Inbox
                    expect($("#threadlist").html()).toContain("INBOX ZERO");
                    //Unread
                    threadsColl.state.threadAreas.changeActive(unread);
                    //Force the render -- the lazy render (debaounce) of 300ms to prevent unnecessary empty views due to latency needs to be overridden for testing purposes
                    threadlistView.render();
                    expect($("#threadlist").html()).toContain("No unread messages");
                    //Archive
                    threadsColl.state.threadAreas.changeActive(archive);
                    //Force the render -- same
                    threadlistView.render();
                    expect($("#threadlist").html()).toContain("No archived messages");
                });



                describe("Tests needing multiple pages > ", function() {
                    beforeEach(function() {
                        threadsColl.reset(threadlist_full);
                    });
                    it("should be able to update the page within State, forward or back", function() {

                        spyOn(threadsColl.state, 'updatePage');

                        threadsColl.state.updatePage.calls.reset();

                        //fake event with noop
                        var e = {
                            preventDefault: function() {

                            }
                        };
                        threadlistView.nextPage(e);

                        //The actual changing of the page requires hitting the router, which we're not testing here

                        expect(threadsColl.state.updatePage).toHaveBeenCalled();

                        threadsColl.state.updatePage.calls.reset();

                        threadlistView.prevPage(e);

                        expect(threadsColl.state.updatePage).toHaveBeenCalled();
                    });

                    it("should return the IDs of selected / active threads", function() {
                        var thread13 = threadsColl.findWhere({
                            id: 13
                        });

                        thread13.toggle();

                        expect(threadlistView.activeIDs()).toEqual("13");
                    });

                    it("should Mark As Read either selected threads or all threads accordingly", function() {

                        var thread13 = threadsColl.findWhere({
                            id: 13
                        });

                        thread13.set({
                            read: false
                        }).toggle();

                        spyOn(threadsColl, "trigger").and.callThrough();
                        spyOn(threadlistView, "modSelected").and.callThrough();
                        spyOn(threadlistView, "modAll").and.callThrough();

                        threadlistView.markReadSelected(false);

                        expect(threadlistView.modSelected).toHaveBeenCalled();

                        expect(threadsColl.trigger).toHaveBeenCalled();

                        threadsColl.trigger.calls.reset();

                        threadlistView.markReadSelected(true);

                        expect(threadlistView.modAll).toHaveBeenCalled();

                        expect(threadsColl.trigger).toHaveBeenCalled();
                    });

                    it("should Archive either selected threads or all threads accordingly", function() {

                        var thread13 = threadsColl.findWhere({
                            id: 13
                        });

                        thread13.set({
                            read: false
                        }).toggle();

                        spyOn(threadsColl, "trigger").and.callThrough();
                        spyOn(threadlistView, "modSelected").and.callThrough();
                        spyOn(threadlistView, "modAll").and.callThrough();

                        threadlistView.archiveSelected(false);

                        expect(threadlistView.modSelected).toHaveBeenCalled();

                        expect(threadsColl.trigger).toHaveBeenCalled();

                        threadsColl.trigger.calls.reset();

                        threadlistView.archiveSelected(true);

                        expect(threadlistView.modAll).toHaveBeenCalled();

                        expect(threadsColl.trigger).toHaveBeenCalled();
                    });

                    it("should select and deselect all", function() {
                        expect(threadsColl.where({
                            active: true
                        }).length).toBe(0);

                        threadlistView.selectAll();

                        expect(threadsColl.where({
                            active: true
                        }).length).toBe(threadsColl.length);

                        threadlistView.unselectAll();

                        expect(threadsColl.where({
                            active: true
                        }).length).toBe(0);
                    });
                });
            });
        });

        describe("Messages & Controller >", function(argument) {

            /*

            Messages are the children of Threads -- an individual piece of content (text, media) sent through the system to a group or individual.

            Messages support oembed, and are created using the Compose module, which relies on bootstraps modal plugin.

            */

            describe("Messages classes >", function() {

                var messages, server;

                beforeEach(function() {
                    messages = Inbox.module("Messages");
                    server = sinon.fakeServer.create();
                    server.respondWith("GET", "/messages/4/json/", [200, {
                            "Content-Type": "application/json"
                        },
                        JSON.stringify(messages_json)
                    ]);
                    server.autoRespond = true;
                });

                afterEach(function() {
                    server.restore();
                });

                describe("Message model >", function() {

                    it("should set the message to scrunched if it is not active or not meant to be clickable", function() {

                        var message = new messages.Message(messages_json.connectmessages[1]);

                        message.set({
                            "read": true
                        });

                        expect(message.get("scrunched")).toBeFalsy();

                        message.setScrunch();

                        expect(message.get("scrunched")).toBe(true);

                        //reset
                        message.set({
                            "scrunched": ""
                        });
                        message.toggle();

                        message.setScrunch();

                        expect(message.get("scrunched")).toBeFalsy();
                    });
                });
                describe("Messages collection >", function() {

                    var messagesColl;

                    beforeEach(function(done) {

                        messagesColl = new messages.Messages(false, {
                            id: 4,
                            url: "/messages/4/json/"
                        });

                        messagesColl.fetch().success(function() {
                            done();
                        });
                    });

                    it("should set the messages as cached after fetching, and setup scrunching", function() {

                        spyOn(messagesColl, "trigger");
                        spyOn(messagesColl, "scrunch");

                        messagesColl.afterFetch();

                        expect(messagesColl.cached).toBe(true);

                        expect(messagesColl.read.length).toBeGreaterThan(5);

                        expect(messagesColl.scrunch).toHaveBeenCalled();

                        expect(messagesColl.trigger).toHaveBeenCalledWith("fetchComplete");
                    });

                    it("should be able to scrunch and unscrunch", function() {
                        messagesColl.scrunch();

                        expect(messagesColl.read[0].get("scrunchToggle")).toBe(true);

                        //2 = One scrunch toggle and one unread
                        expect(messagesColl.where({
                            scrunched: true
                        }).length).toBe(messagesColl.length - 2);

                        messagesColl.unscrunch();

                        expect(messagesColl.where({
                            scrunched: true
                        }).length).toBe(0);
                    });
                });
                describe("Message view >", function() {
                    var message, messageView;
                    beforeEach(function() {
                        message = new messages.Message(messages_json.connectmessages[1]);
                        message.set("read", "false");

                        messageView = new messages.MessageView({
                            model: message
                        });
                    });
                    it("should make all external links open in a new window", function() {
                        var newDiv, link, linkInContent;

                        window.CONNECT = window.CONNECT || {};

                        window.CONNECT.icon_prefix = "icon icon-";

                        newDiv = $("<div />");

                        newDiv.html(message.get("text"));

                        link = newDiv.find('a');

                        expect(link.attr("href")).toContain("http://www.google.com/");
                        expect(link.attr("target")).toBeFalsy();

                        messageView.render();
                        messageView.linkBlanker();

                        linkInContent = messageView.$el.find('.msg-content a')[0];

                        expect($(linkInContent).attr("href")).toContain("http://www.google.com/");
                        expect($(linkInContent).attr("target")).toBe("_blank");
                    });
                });
                describe("Message list view >", function() {
                    var messagesColl, messagesView;

                    beforeEach(function(done) {

                        messagesColl = new messages.Messages(false, {
                            id: 4,
                            url: "/messages/4/json/"
                        });

                        messagesColl.fetch().success(function() {
                            done();
                        });

                        messagesView = new messages.MessagesView({
                            collection: messagesColl
                        });
                    });

                    it("should call oembed on render if the message is cached", function() {
                        spyOn(messagesView, "oembed");

                        messagesView.render();

                        expect(messagesView.oembed).toHaveBeenCalled();
                    });

                    it("should trigger an action for Archiving", function() {
                        spyOn(messagesView, "trigger");

                        messagesView.$el.find(".archive").click();

                        expect(messagesView.trigger).toHaveBeenCalled();
                    });

                    it("should trigger an action for Flagging", function() {
                        spyOn(messagesView, "trigger");

                        messagesView.flag();

                        expect(messagesView.trigger).toHaveBeenCalled();
                    });

                    it("should trigger an action for going back to the thread preview list", function() {
                        spyOn(messagesView, "trigger");

                        messagesView.$el.find(".back-to-inbox").click();

                        expect(messagesView.trigger).toHaveBeenCalledWith("back");
                    });

                    describe("Compose >", function() {

                        var composeRoute;

                        beforeEach(function(done) {
                            messagesView.render();
                            $("#thread-detail").append(messagesView.$el);

                            composeRoute = sinon.fakeServer.create();

                            composeRoute.respondWith("GET", "/messages/create/?embed=yes", [200, {
                                    "Content-Type": "text/html; charset=utf-8"
                                },
                                "<p>Reply content</p>"
                            ]);
                            composeRoute.autoRespond = true;

                            messagesView.$el.find(".compose").click();

                            $("#compose").on("shown.bs.modal", function() {
                                done();
                            });
                        });

                        afterEach(function() {
                            $("#thread-detail").empty();
                            $("#compose").empty();
                            composeRoute.restore();
                        });

                        it("should bind the Compose object to the compose button", function() {
                            expect($("#compose").hasClass("in")).toBe(true);
                            expect($("#compose").html()).toContain("Reply content");
                        });
                    });

                });
            });
            describe("Controller and router", function() {
                var controller, router;

                beforeEach(function() {
                    var controlMod = Inbox.module("Controller");
                    controller = new controlMod.Controller();
                    router = new controlMod.Router({
                        controller: controller
                    });
                    controller.router = router;
                    Backbone.history.start({
                        root: "/",
                        pushState: true
                    });

                    window.CONNECT.user.groups = [{
                        name: "Cats Group",
                        shortname: "Cats...",
                        id: 1,
                        query: "&group=1",
                        category: "cats"
                    }, {
                        name: "Dogs group",
                        shortname: "Dogs group",
                        id: 2,
                        query: "&group=2",
                        category: "dogs"
                    }, {
                        name: "Pizza Dog Group, starring Lucky the Pizza Dog",
                        shortname: "Pizza Dog Group",
                        id: 3,
                        query: "&group=3",
                        category: "pizza"
                    }];
                });

                afterEach(function() {
                    Backbone.history.stop();
                });

                describe("Router", function() {

                    it("should redirect the root URL to the inbox", function() {
                        spyOn(Backbone.history, "navigate");

                        router.redir();

                        expect(Backbone.history.navigate).toHaveBeenCalledWith("inbox/", Object({
                            trigger: true
                        }));
                    });
                    it("should change the area by updating the Thread Area and Groups models", function() {
                        router.changeArea("Archive");

                        expect(controller.threadAreas.findWhere({
                            active: true
                        }).get("name")).toBe("Archive");

                        router.changeArea("Archive", 2);

                        expect(controller.groups.findWhere({
                            active: true
                        }).get("name")).toBe("Dogs group");
                    });
                });
                describe("Controller", function() {
                    it("should, on init, get the applications models setup with proper defaults", function() {
                        expect(controller.threadAreas instanceof Backbone.Collection).toBe(true);
                        expect(controller.groups instanceof Backbone.Collection).toBe(true);
                        expect(controller.threads instanceof Backbone.Collection).toBe(true);
                        expect(controller.store instanceof Backbone.Collection).toBe(true);
                        expect(controller.modStore instanceof Backbone.Collection).toBe(true);
                        expect(controller.threadAreas.length).toBe(3);
                        expect(controller.groups.length).toBe(3);
                    });

                    describe("showDetail", function() {
                        beforeEach(function() {
                            messages = Inbox.module("Messages");
                            server = sinon.fakeServer.create();
                            server.respondWith("GET", "/messages/4/json/", [200, {
                                    "Content-Type": "application/json"
                                },
                                JSON.stringify(messages_json)
                            ]);
                            server.autoRespond = true;
                        });

                        afterEach(function() {
                            server.restore();
                        });

                        it("should add a message to the store & change the body class for the detail view", function() {
                            //stubs navigate and stops security error in Phantom JS
                            spyOn(controller.router, "navigate");

                            controller.moderate(4, 3);

                            expect($("body").hasClass("detail")).toBe(true);

                            expect(controller.modStore.findWhere({
                                id: 4
                            })).toBeTruthy();
                        });
                        it("should add a message to the store & change the body class for the moderation view", function() {
                            //stubs navigate and stops security error in Phantom JS
                            spyOn(controller.router, "navigate");

                            controller.showDetail(4, false);

                            expect($("body").hasClass("detail")).toBe(true);

                            expect(controller.store.findWhere({
                                id: 4
                            })).toBeTruthy();
                        });
                    });


                    it("should set up the sidebar views correctly based on if the screen is in mobile mode or not", function() {
                        window.mobileChange = function() {};

                        controller.start();
                        controller.setViews(false);

                        expect(Inbox.areas.hasView()).toBe(true);
                        expect(Inbox.areasMobile.hasView()).toBe(false);
                        expect(Inbox.groups.hasView()).toBe(true);
                        expect(Inbox.groupsMobile.hasView()).toBe(false);

                        controller.setViews(true);

                        expect(Inbox.areas.hasView()).toBe(false);
                        expect(Inbox.areasMobile.hasView()).toBe(true);
                        expect(Inbox.groups.hasView()).toBe(false);
                        expect(Inbox.groupsMobile.hasView()).toBe(true);
                    });
                    it("should change the page title accordingly", function() {
                        controller.changeTitle("Pizza Dog");

                        expect(document.title).toBe("Connect | Pizza Dog");
                    });

                    it("should create correct POST actions based on the information it gets from triggers", function() {

                        controller.csrf = "123456";

                        spyOn($, "post").and.callThrough();

                        controller.post("/my-url/", {
                            "test": "value"
                        }, "nothing");

                        expect($.post).toHaveBeenCalledWith("/my-url/", Object({
                            "test": "value",
                            "csrfmiddlewaretoken": "123456"
                        }));

                    });
                });
            });
        });
    });
});
