function startIntro() {

    intro = introJs();
    intro.setOptions({
        steps: [{
            intro: "<h2>Congratulations!</h2><p>Thanks for joining Connect.</p>"
        }, {
            element: '.explore-groups',
            intro: "<h2>Search for Groups</h2><p>Find groups to join by keyword or location. </p>"
        }, {
            element: '.category-group',
            intro: "<h2>Filter your results</ h2><p>Easily filter groups by category.</p>",
            position: 'right'
        }, {
            element: document.querySelectorAll('.item')[0],
            intro: '<h2>Join a Group</h2><p>Click the "Join Group" button, or click on a group\'s name to learn more about it.</p>',
            position: 'right'
        }, {
            element: document.querySelectorAll('.item')[1],
            intro: '<h2>Join a National Group</h2><p>National groups are a great way to have meaningful conversations with supporters across the country.</p>',
            position: 'left'
        }, {
            element: '.navbar-nav .threads',
            intro: '<h2>Messages</h2><p>Read threads and send messages to groups that you\'ve joined.</p>',
            position: 'bottomRight'
        }, {
            element: '.navbar-nav .my-profile',
            intro: '<h2>Your profile</h2><p>Edit your profile and manage your groups and subscription settings.</p>',
            position: 'bottomRight'
        }, {
            element: '.disclaimer-links .take-tour',
            intro: '<h2>You can always get back to the tour here.</>',
            position: 'top'
        }],
        exitOnOverlayClick: false,
        showStepNumbers: false,
        nextLabel: 'Next',
        tooltipClass: 'tutorial',
        scrollToElement: true,
        showButtons: false,
        showBullets: false
    });

    var tourLength = intro._options.steps.length - 1;

    var $nothanks = $('<a class="no-thanks introjs-button" href="#">No Thanks</a>');

    var $nextStep = $('<a class="next-step introjs-button" href="#">Take a Tour</a>');

    var $okgotit = $('<a class="ok-got-it introjs-button" href="#">OK, got it!</a>');

    var $buttonset = $('<div class="button-set"></div>');

    var $lastbuttonset = $buttonset.clone();

    $nothanks.click(function() {
        $buttonset.detach();
        $("html, body").animate({
            scrollTop: $(document).height()
        }, "slow");
        intro.goToStep(tourLength).start();
    });

    $nextStep.click(function() {
        intro.setOptions({
            'showButtons': true,
            'showBullets': true
        });
        intro.nextStep();

    });

    $okgotit.click(function() {
        intro.exit();
        $('.introjs-overlay').remove();
    });

    $buttonset.append($nextStep).append($nothanks).append('<small>Don\'t worry, you can always get to it later.</small>');

    $lastbuttonset.append($okgotit);

    //On Tooltip

    intro.onbeforechange(function() {
        if (intro._currentStep > 0 && intro._currentStep < tourLength) {
            intro.setOptions({
                'showButtons': true,
                'showBullets': true
            });
        } else {
            intro.setOptions({
                'showButtons': false,
                'showBullets': false
            });
        }
    });

    intro.ontooltip(function(tooltip) {
        if (intro._currentStep == 0) {
            $(tooltip).append($buttonset);
        } else if (intro._currentStep == tourLength) {
            $(tooltip).append($lastbuttonset);
            $(tooltip).css('top', '-240px');
        } else {
            $buttonset.detach();
            $lastbuttonset.detach();
        }
    });

    intro.onexit(function() {
        $('html,body').animate({
            scrollTop: 0
        });
        $.post(CONNECT.services.tour, {
            csrfmiddlewaretoken: $("[name=csrfmiddlewaretoken]").val()
        }, 'json');
    });

    intro.start();
}

startIntro();