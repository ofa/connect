//Polyfills
if (!Function.prototype.bind) {
    Function.prototype.bind = function(oThis) {
        if (typeof this !== "function") {
            // closest thing possible to the ECMAScript 5 internal IsCallable function
            throw new TypeError("Function.prototype.bind - what is trying to be bound is not callable");
        }

        var aArgs = Array.prototype.slice.call(arguments, 1),
            fToBind = this,
            fNOP = function() {},
            fBound = function() {
                return fToBind.apply(this instanceof fNOP && oThis ? this : oThis,
                    aArgs.concat(Array.prototype.slice.call(arguments)));
            };

        fNOP.prototype = this.prototype;
        fBound.prototype = new fNOP();

        return fBound;
    };
}

if (!Array.prototype.indexOf) {
    Array.prototype.indexOf = function(elt /*, from*/ ) {
        var len = this.length >>> 0;
        var from = Number(arguments[1]) || 0;
        from = (from < 0) ? Math.ceil(from) : Math.floor(from);
        if (from < 0) from += len;
        for (; from < len; from++) {
            if (from in this && this[from] === elt)
                return from;
        }
        return -1;
    };
}

function alertTimeout(myAlert) {
    setTimeout(function() {
        myAlert.slideUp('slow');
    }, 10000);
}

function c() {
    var detect = [38, 40, 38, 40, 38, 40, 38, 40, 38, 40],
        place = 0;

    function d(key_code) {
        if (key_code == detect[place]) {
            place += 1;
            if (place == detect.length) {
                $('<div class="modal" id="kgif"><div class="modal-body"><img src="http://s3.amazonaws.com/origin.assets.bostatic.com/apps/messages-prod/static/img/k.gif"></div></div>').modal().appendTo("body").show();
            }
        } else {
            place = 0;
        }
    }

    $(document).keyup(function(e) {
        d(e.keyCode);
    });
}


function mobileClassing(newmobile) {
    if (newmobile) {
        $('body').addClass('mobile');
    } else {
        $('body').removeClass('mobile');
    }
}

function mobileChange() {
    var newmobile = $(window).width() < 768;
    if (!CONNECT.mobile || newmobile != CONNECT.mobile) {
        $(window).trigger('mobileSwitch', newmobile);
    }
    CONNECT.mobile = newmobile;
    return newmobile;
}

$(function() {
    window.ga = window.ga || function() {
        (window.ga.q = window.ga.q || []).push(arguments);
    };

    c();
    alertTimeout($('.alert'));

    // If the user is anonymous, do not initalize a badge that will check for
    // new messages. An anonymous user cannot have messages.
    if (!CONNECT.user.anonymous) {
        CONNECT.badge = new Badge('.navbar-fixed-top .threads a', CONNECT.services.unread, 15000);
        CONNECT.badge.init();
    }

    mobileChange();

    $(window).resize(function(e) {
        mobileChange();
    });
});