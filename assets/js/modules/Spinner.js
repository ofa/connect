var Spinner = function(element, initialValue) {
    if (element instanceof jQuery) {
        this.$el = element; //jquery already passed in!    
    } else {
        this.$el = $(element); //else, jquerify it
    }

    this.value = initialValue;

    this.$input = this.$el.find('input');

    this.init();
}

Spinner.prototype.init = function() {

    this.set(this.value);

    this.$el.find('.up').click(function(e) {
        e.preventDefault();
        this.increase();
    }.bind(this));

    this.$el.find('.down').click(function(e) {
        e.preventDefault();
        this.decrease();
    }.bind(this));

    this.$el.on("keyup keypress", function(e) {
        var code = e.keyCode || e.which;
        if (code == 13) {
            e.preventDefault();
            this.set(this.$input.val());
            this.$el.trigger("spinner.manualSet", this.value);
        }

    }.bind(this));

    return this;
}

Spinner.prototype.updateView = function(value) {

    this.$input.val(value);

    return this;
}

Spinner.prototype.set = function(value) {

    this.value = value;

    this.updateView(value);

    return this;
}

Spinner.prototype.increase = function() {

    this.value++;

    this.updateView(this.value);

    this.$el.trigger("spinner.increased", this.value);

    return this;
}

Spinner.prototype.decrease = function() {
    if (this.value - 1 <= 0) return this;

    this.value--;

    this.updateView(this.value);

    this.$el.trigger("spinner.decreased", this.value);

    return this;
}