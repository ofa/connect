//Open a modal with a compose window
//Requires boostrap modal component.

var Compose = function(element) {
    if (element instanceof jQuery) {
        this.$el = element; //jquery already passed in!    
    } else {
        this.$el = $(element); //else, jquerify it
    }

    this.init();
};

Compose.prototype.init = function() {
    var that = this;

    this.modern = !!document.addEventListener;

    var template = "<div class='modal fade' id='compose' tabindex='-1' role='dialog' aria-labelledby='composeLabel' aria-hidden='true'><div class='modal-dialog modal-lg'><div class='modal-content'><div class='modal-body'></div></div></div></div>";

    if (!$("#compose").length) {
        $("body").append(template);
    }

    this.$el.each(function() {

        var url = $(this).attr("href") + "?embed=yes";

        $(this).attr("data-reply-url", url);

        $(this).click(function(e) {
            e.preventDefault();
            that.fetch(url);
        });

    });
};

Compose.prototype.fetch = function(url) {
    $.get(url).done(function(data) {
        this.populateWindow(data);
    }.bind(this));
};

Compose.prototype.populateWindow = function(data) {

    var that = this;

    var $composeWindow = $("#compose");

    $composeWindow.find(".modal-body").html(data);

    var message_form = $("#message_form");

    this.$form = message_form;

    function handle_image_upload_response(image, json) {
        message_form.append("<input type='hidden' name='images' value='" + json.id + "' />");
    }
    var tokenvalue = $("[name='csrfmiddlewaretoken']").attr("value");

    if (this.modern) {
        $("#id_text").redactor({
            minHeight: 200,
            buttons: ["bold", "italic", "|", "link", "image"],
            allowedTags: ["br", "a", "em", "strong", "img", "b", "i"],
            allowedAttr: [
                ["a", ["class", "href", "title", "target", "data-embed"]],
                ["img", ["class", "href", "src", "target", "id"]]
            ],
            linebreaks: true,
            plugins: ["oembed"],
            imageUpload: CONNECT.services.upload,
            imageUploadCallback: handle_image_upload_response,
            uploadImageFields: {
                "csrfmiddlewaretoken": tokenvalue
            },
            convertImageLinks: true,
            convertVideoLinks: true
        });
    }

    if (!!localStorage.getItem("subject") && localStorage.getItem("subject") !== "undefined") {
        $("#id_subject").val(localStorage.getItem("subject"));
    }

    if (!!localStorage.getItem("message") && localStorage.getItem("message") !== "undefined") {

        $("#id_text").redactor("code.set", localStorage.getItem("message"));
    }
    if (!!localStorage.getItem("group") && localStorage.getItem("group") !== "undefined") {
        $("#id_group").val(localStorage.getItem("group"));
    }

    $composeWindow.modal("show");

    $composeWindow.on("shown.bs.modal", function(e) {

        this.messageType = message_form.data("message-type");

        this.to = null;

        if (this.messageType !== "new-message") {
            this.to = message_form.data("group") == undefined ? message_form.data("recipient") : message_form.data("group");
        }

        this.$el.trigger("compose.shown");

    }.bind(this));

    if (this.modern) {
        $composeWindow.on("hide.bs.modal", function(e) {
            var subj = $("#id_subject").val();
            var msgText = $("#id_text").redactor("code.get");
            var group = $("#id_group").val();

            // Put the object into storage
            localStorage.setItem("subject", subj);
            localStorage.setItem("message", msgText);
            localStorage.setItem("group", group);
        });

    }

    message_form.submit(function(e) {
        e.preventDefault();

        if (that.modern) {
            $("#id_text").redactor("code.set", $("#id_text").redactor("code.get") + "<!-- vars:redactor=true -->");
            localStorage.removeItem("subject");
            localStorage.removeItem("message");
            localStorage.removeItem("group");
        }
        $(this).find("input[type=submit]").remove();
        $(this).find(".loading").show();
        if (that.to === null) {
            that.to = $("#id_group").val();
        }
        that.$el.trigger("compose.sent", [that.messageType, that.to]);
        $(this).off();
        $(this).submit();
    });

}
