// modified Isotope methods for gutters in masonry
$.Isotope.prototype._getMasonryGutterColumns = function() {
    var gutter = this.options.masonry && this.options.masonry.gutterWidth || 0;
    containerWidth = this.element.width();

    this.masonry.columnWidth = this.options.masonry && this.options.masonry.columnWidth ||
        // or use the size of the first item
        this.$filteredAtoms.outerWidth(true) ||
        // if there's no items, use size of container
        containerWidth;

    this.masonry.columnWidth += gutter;

    this.masonry.cols = Math.floor((containerWidth + gutter) / this.masonry.columnWidth);
    this.masonry.cols = Math.max(this.masonry.cols, 1);
};

$.Isotope.prototype._masonryReset = function() {
    // layout-specific props
    this.masonry = {};
    // FIXME shouldn't have to call this again
    this._getMasonryGutterColumns();
    var i = this.masonry.cols;
    this.masonry.colYs = [];
    while (i--) {
        this.masonry.colYs.push(0);
    }
};

$.Isotope.prototype._masonryResizeChanged = function() {
    var prevSegments = this.masonry.cols;
    // update cols/rows
    this._getMasonryGutterColumns();
    // return if updated cols/rows is not equal to previous
    return (this.masonry.cols !== prevSegments);
};

var Isogroup = function(element, options) {
    this.$el = $(element);
    defaults = {
        itemSelector: '.item',
        masonry: {
            columnWidth: 270,
            gutterWidth: 15
        }
    };
    this.options = $.extend(defaults, options);
    this.init();
};

Isogroup.prototype.init = function() {
    var $el = this.$el;

    var imgLoad = $el.imagesLoaded(function(images) {
        if ($(window).width() > 767) {
            $el.isotope(this.options);
        }
    }.bind(this));

    var mobile = $(window).width() < 767 ? true : false;

    $(window).on('mobileChange', function(e, mobile) {
        if (mobile) {
            $el.isotope('destroy');
        } else {
            $el.isotope(this.options);
        }
    });
}

Isogroup.prototype.filter = function(list) {

    var listString = list.toString();

    if (listString != '') {
        this.$el.isotope({
            filter: listString
        });
    } else {
        this.$el.isotope({
            filter: "*"
        });
    }
};