var map;

//Utility functions

function toMiles(value) {
    return (Math.round((value / 1000) * 0.621371) * 10) / 10;
}

function toMeters(value) {
    return parseFloat(value, 10) * 1.6093 * 1000;
}

//===========================

var Map = function(element) {
    if (element instanceof jQuery) {
        this.$el = element; //jquery already passed in!
        this.el = this.$el[0];
    } else {
        this.el = element;
        this.$el = $(element); //else, jquerify it
    }

    this.init();
}

Map.prototype.init = function() {
    //flag for functions only run on setup; i.e. event handlers
    this.setup = true;

    this.fields = {};
    this.properties = {};

    this.$class = $('.form-location');

    //hidden fields
    this.fields.$lat = $('#id_group_form-latitude');
    this.fields.$lng = $('#id_group_form-longitude');
    this.fields.$rad = $('#id_group_form-radius');
    this.fields.$checkbox = $('#location_toggle');

    this.spinner = new Spinner('.spinner', 25);

    //Visible fields

    this.fields.$address = $('#id_group_form-address');
    this.fields.$display = $('#id_group_form-display_location');

    this.properties.rad = this.fields.$rad.val();

    this.circle;

    this.properties.isNew = isNew; //global set by Django template

    this.properties.hasLocation = this.properties.isNew || this.fields.$lat.val() != '';

    if (this.properties.hasLocation) {
        this.properties.latLng = new google.maps.LatLng(this.fields.$lat.val(), this.fields.$lng.val());
    }

    this.map = new google.maps.Map(this.$el[0], {
        zoom: 8,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });

    this.toggleSetup();

    this.setInitialLocation();

    this.$el.on('propChange', function() {
        this.render();
    }.bind(this));

    this.$el.on('propReset', function() {
        this.updateFields();
    }.bind(this));

    return this;
}

Map.prototype.render = function() {

    this.placeMarker();

    this.updateFields();

    if (this.setup) {
        this.events();
    }

    return this;
}

Map.prototype.events = function() {

    google.maps.event.addListener(this.map, 'click', function(event) {
        this.setProperties({
            latLng: event.latLng
        });
        ga('send', 'event', 'Map Action', 'Map clicked', event.latLng);
    }.bind(this));

    this.fields.$address.click(function() {
        $(this).val('');
    }).submit(function(e) {
        e.preventDefault();
        $('.address .btn').click();
    }).on("keyup keypress", function(e) {
        var code = e.keyCode || e.which;
        if (code == 13) {
            e.preventDefault();
            $('.address .btn').click();
        }
    });

    $('.address .btn').click(function() {
        ga('send', 'event', 'Map Action', 'Address button submitted', this.fields.$address.val());
        this.setProperties({
            address: this.fields.$address.val()
        });
    }.bind(this));

    this.spinner.$el.on("spinner.increased spinner.decreased spinner.manualSet", function(e, spinVal) {
        ga('send', 'event', 'Map Action', 'Radius changed via spinner', spinVal);
        this.setProperties({
            rad: toMeters(spinVal)
        });

    }.bind(this));

    this.setup = false;

    return this;
};

Map.prototype.setProperties = function(obj) {
    var deferred = $.Deferred();
    //update state -- 

    if (obj.latLng) {

        if (obj.latLng != "reset") {
            this.properties.latLng = obj.latLng;
            $.when(this.geocode({
                'latLng': obj.latLng
            })).then(function(results) {
                this.properties.address = results[0].formatted_address;
                this.properties.display_loc = results[1].formatted_address.replace(/, USA/, '');
                deferred.done(this.$el.trigger('propChange'))
                deferred.resolve();
            }.bind(this));

        } else {
            this.properties.latLng = '';
            this.$el.trigger('propReset');
        }
    }

    if (obj.rad) {

        if (obj.rad != "reset") {
            this.properties.rad = obj.rad;
            this.$el.trigger('propChange');
        } else {
            this.properties.rad = '';
            this.$el.trigger('propReset');
        }
    }

    if (obj.address) {
        if (obj.rad != "reset") {
            this.properties.address = obj.address;
            this.properties.display_loc = obj.address;

            $.when(this.geocode({
                'address': obj.address
            })).then(function(results) {

                this.properties.latLng = results[0].geometry.location;

                deferred.done(this.$el.trigger('propChange'));
                deferred.resolve();
            }.bind(this));
        } else {
            this.properties.address = '';
            this.properties.display_loc = '';
        }
    }

    ga('send', 'event', 'Map Action', 'Map updated', this.properties.address);

    return this;
};

Map.prototype.toggleSetup = function() {
    this.fields.$checkbox.change(function(e) {
        if (this.fields.$checkbox.is(":checked")) {
            this.$class.show();
            this.properties.hasLocation = true;
            this.setInitialLocation();
        } else {

            this.reset();
        }
    }.bind(this));
};

Map.prototype.reset = function() {
    this.$class.hide();

    this.fields.$checkbox.prop("checked", false);

    this.setProperties({
        latLng: "reset",
        rad: "reset",
        address: "reset"
    });

    this.properties.hasLocation = false;

    this.properties.isNew = true;

};

Map.prototype.updateFields = function() {

    //hidden fields

    if (this.properties.latLng != '') {
        this.fields.$lat.val(this.properties.latLng.lat());
        this.fields.$lng.val(this.properties.latLng.lng());
        this.fields.$address.val(this.properties.address);
        if (this.properties.isNew) {
            this.fields.$display.val(this.properties.display_loc);
        }

    } else {
        this.fields.$lat.val('');
        this.fields.$lng.val('');
        this.fields.$address.val('');
        this.fields.$display.val('');
    }

    if (this.properties.rad != '') {
        this.fields.$rad.val(toMiles(this.properties.rad));
    } else {
        this.fields.$rad.val('');
    }

    //update Spinner
    this.spinner.set(toMiles(this.properties.rad));
};

Map.prototype.setInitialLocation = function() {
    if (!this.properties.isNew) { //Edit existing group - no geolocate

        if (this.properties.hasLocation) {

            this.setProperties({
                latLng: this.properties.latLng,
                rad: toMeters(this.properties.rad),
                resize: true
            });
        } else {
            this.reset();
        }

    } else { //new group

        $.when(this.getUserLocation())

        .then(function(position) {

            this.properties.latLng = new google.maps.LatLng(position.coords.latitude,
                position.coords.longitude);

            this.map.setCenter(this.properties.latLng);

            this.setProperties({
                latLng: this.properties.latLng,
                rad: toMeters(25)
            });

        }.bind(this),
        function(){

            this.properties.latLng = new google.maps.LatLng(41.877256, -87.620125);

            this.map.setCenter(this.properties.latLng);

            this.setProperties({
                latLng: this.properties.latLng,
                rad: toMeters(55)
            });

        }.bind(this));
    }
    return this;
}

Map.prototype.getUserLocation = function() {
    var deferred = $.Deferred();
    if (navigator.geolocation) {

        navigator.geolocation.getCurrentPosition(
            deferred.resolve,
            deferred.reject);

    } else {

        //Display an error message

        var output = Mustache.render($('#alertTemplate').html(), {
            message: 'We tried to find your location automatically, but your browser doesn\'t support geolocation. Please set a location for your group.'
        });

        $('#main').prepend(output);
        var myAlert = $('.alert-new.hidden');
        myAlert.slideDown('slow', 'easeOutExpo').removeClass('alert-new hidden');
        alertTimeout(myAlert);

        deferred.reject();
    }

    return deferred.promise();
}

Map.prototype.placeMarker = function() {
    if (this.circle instanceof google.maps.Circle) {
        //If circle exists, remove existing instance
        this.circle.setMap(null);
    }

    this.circle = new google.maps.Circle({
        center: this.properties.latLng,
        radius: this.properties.rad,
        editable: true,
        fillColor: '#008FC5',
        strokeColor: '#008FC5'
    });

    this.circle.setMap(this.map);

    google.maps.event.addListener(this.circle, 'radius_changed', function(event) {
        this.setProperties({
            rad: this.circle.getRadius()
        });
        ga('send', 'event', 'Map Action', 'Radius adjusted via map', this.circle.getRadius());
    }.bind(this));

    google.maps.event.addListener(this.circle, 'center_changed', function(event) {
        this.setProperties({
            latLng: this.circle.getCenter()
        });
        ga('send', 'event', 'Map Action', 'Radius dragged to new location', this.circle.getCenter());
    }.bind(this));

    this.map.fitBounds(this.circle.getBounds());

    if (this.setup){
        google.maps.event.trigger(this.map, 'resize');    
    }
    

    return this;
};

Map.prototype.geocode = function(obj) {
    var deferred = $.Deferred();
    geocoder.geocode(obj, deferred.resolve);
    return deferred.promise();
};

$(document).ready(function() {
    $("#map_canvas").css("height", "300px");

    google.load("maps", "3", {
        "callback": setup,
        other_params: "sensor=false"
    });

    function setup() {
        geocoder = new google.maps.Geocoder();

        map = new Map("#map_canvas");

    }
});