/*
NOTES: It would be good if the markup for the element was actually created based on key value pairs passed in on initialization.
*/

var Filter = function(element, list, func) {
    this.$el = $(element);
    this.func = func;
    this.list = list;
    this.init();
};

Filter.prototype.init = function(){
	var that = this;
	this.$el.find('input[type=checkbox]').change(function() {
		that.applyFilter();
    });
}
 
Filter.prototype.applyFilter = function() {
    var list = [];
    this.$el.find('input:checked').each(function() {
        var chkVal = "." + $(this).attr('data-category');
        list.push(chkVal);
    });
    this.func(list);
}