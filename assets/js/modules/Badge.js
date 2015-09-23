var Badge = function(element, url, interval) {
    if (!(this instanceof Badge)) {
        return new Badge(element);
    }
    this.ready = $.Deferred();
    this.$el = $(element);
    this.url = url;
    this.status = "focus";
    this.interval = interval;
    this.focusInterval = interval;
    this.blurInterval = interval * 8;
    this.count = 0;
    this.$el.append('<span class="badge"></span>');
    this.$badge = this.$el.find('.badge');
    this.first = true;
    this.ready.resolve(this);
    
};

Badge.prototype.updateCount = function(count) {
    this.$badge.empty();
    var oldCount = this.count;
    this.count = parseInt(count, 10);
    if (this.count > 0) this.$badge.html(this.count);
    if (this.count > oldCount && !this.first) {
        this.$el.trigger("updated");
        $(window).trigger("badgeUpdated");
    }
    if (this.first) this.first = false;
    return this.count;
};

Badge.prototype.fetch = function() {
    return $.get(this.url)
};

Badge.prototype.cycle = function() {
    this.fetch().then(function(data) {
        this.updateCount(data.unread_count);
    }.bind(this));
};

Badge.prototype.markRead = function(num) {
    this.count = this.count - num;
    this.updateCount(this.count);
};

Badge.prototype.repeatCycle = function(status) {
    if (this.repeat){
        window.clearInterval(this.repeat);
    }

    this.interval = status == "focus" ? this.focusInterval : this.blurInterval;

    this.repeat = setInterval(function() {
        return this.cycle();
    }.bind(this), this.interval);
}


Badge.prototype.init = function() {
    var me = this;

    $(window).on("blur focus", function(e) {
        if (me.status != e.type) {
            me.status = e.type;
            me.repeatCycle(me.status);
        }
    });

    this.cycle();

    this.repeatCycle(this.status);
};