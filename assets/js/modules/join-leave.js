$(document).ready(function() {
    window.ga = window.ga || function() {
        (window.ga.q = window.ga.q || []).push(arguments);
    };
});
var csrf_token = $("[name='csrfmiddlewaretoken']").val();

$(".join-group").click(function() {
    var that = this;
    $.post(CONNECT.services.subscribe, {
        group_id: $(this).attr('data-group-id'),
        csrfmiddlewaretoken: csrf_token
    }, function(data) {
        $(".join-group-" + data.group_id).html(data.message);
        ga('send', 'event', 'Group Action', 'join', $(that).attr('data-group-id'));
    }, "json");
});

$(".leave-group").click(function() {
    var that = this;
    bootbox.confirm("Are you sure you want to leave this group?", function(result) {
        if (result) {
            $.post(CONNECT.services.unsubscribe, {
                group_id: $(that).attr('data-group-id'),
                csrfmiddlewaretoken: csrf_token
            }, function(data) {
                $(".leave-group-" + data.group_id).html(data.message);
            }, "json");
            ga('send', 'event', 'Group Action', 'leave', $(that).attr('data-group-id'));
        }
    });

});