describe("Badge", function() {
    var server, div, badge, intervalLength, CONNECT;

    beforeEach(function() {
        div = $('<div>');
        CONNECT = {};
        CONNECT.services = {};
        CONNECT.services.unread = "/something";
        intervalLength = 400;
        badge = new Badge(div, CONNECT.services.unread, intervalLength);
    });

    it("should create a new instance of the Badge object", function() {
        expect(badge instanceof Badge).toBeTruthy();
    });

    it("should create a badge structure", function() {
        expect(div.find('.badge').length).toEqual(1);
    });

    it("should update the count based on the new count", function() {
        badge.updateCount(3);
        expect(parseInt(div.find('.badge').html())).toEqual(3);
        badge.updateCount(1);
        expect(parseInt(div.find('.badge').html())).toEqual(1);
        badge.updateCount(0);
        expect(div.find('.badge').html()).toEqual('');
    });

    it("should reduce the count by one when a message is marked read", function() {
        badge.updateCount(3);
        badge.markRead(1);
        expect(parseInt(div.find('.badge').html())).toEqual(2);
        badge.updateCount(1);
        badge.markRead(1);
        expect(div.find('.badge').html()).toEqual('');
    });

    it("should return a promise when fetch is called", function() {
        req = badge.fetch();
        expect(req.then).toEqual(jasmine.any(Function));
    });

    describe("Async functions", function() {
        beforeEach(function() {
            timerCallback = jasmine.createSpy("timerCallback");
            jasmine.clock().install();

            server = sinon.fakeServer.create();
            server.respondWith("GET", "/something", [200, {
                    "Content-Type": "application/json"
                },
                '{"unread_count": 2, "errors": [], "success": true}'
            ]);
            server.autoRespond = true;
        });

        afterEach(function() {
            server.restore();
            jasmine.clock().uninstall();
// 
        });

        it("should update the count when cycle is called", function() {
            var mySpy = sinon.spy();
            badge.cycle();

            jasmine.clock().tick(2000);

            expect(parseInt(div.find('.badge').html())).toEqual(2);

        });

        it("should check the count immediately, and then on the specified interval", function() {
            badge.init();
            server.respond();

            jasmine.clock().tick(2000);

            expect(badge.count).toEqual(2);
            expect(parseInt(div.find('.badge').html())).toEqual(2);
            server.restore();
            server = sinon.fakeServer.create();
            server.respondWith("GET", "/something", [200, {
                    "Content-Type": "application/json"
                },
                '{"unread_count": 3, "errors": [], "success": true}'
            ]);

            jasmine.clock().tick(intervalLength + 200);

            server.respond();

            expect(badge.count).toEqual(3);
            expect(parseInt(div.find('.badge').html())).toEqual(3);

        });
    });
});
