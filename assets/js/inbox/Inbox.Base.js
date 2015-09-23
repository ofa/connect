/*global Backbone */

Inbox.module("Base", function(Base, Inbox, Backbone, Marionette, $, _) {
    "use strict";
    //Extendable models & views
    Base.Model = Backbone.DeepModel.extend({
        defaults: {
            active: false
        },
        toggle: function() {
            this.set("active", !this.isActive());

        },
        isActive: function() {
            return this.get("active");
        }
    });

    Base.ModelView = Marionette.ItemView.extend({
        tagName: "li",
        events: {
            "click": "changeActive"
        },
        modelEvents: {
            "change": "render"
        },
        changeActive: function(e) {
            e.preventDefault();
            this.model.collection.changeActive(this.model);
        }
    });

    Base.Collection = Backbone.Collection.extend({
        model: Base.Model,
        getActive: function() {
            return this.multi ? this.where({
                active: true
            }) : this.findWhere({
                active: true
            });
        },
        deactivate: function() {
            if (!this.getActive() || !!this.multi && !this.getActive().length) return this;
            if (this.multi) {
                _.each(this.getActive(), function(model) {
                    model.set({
                        active: false
                    });
                });
            } else {
                this.getActive().set({
                    active: false
                });
            }
            return this;
        },
        changeActive: function(model) {
            if (this.disallowNull === true && model.isActive()) return;
            if (!this.multi && !model.isActive()) this.deactivate();
            model.toggle();
            this.trigger("changeActive");
            return this;
        }
    });
});
