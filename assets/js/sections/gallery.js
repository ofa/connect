var galleryContainer = $('.gallery-container');

$('.expand').magnificPopup({
    type: 'image',
    gallery: {
        enabled: true,
        preload: 0
    },
    zoom: {
        enabled: true, // By default it's false, so don't forget to enable it
        duration: 300, // duration of the effect, in milliseconds
        easing: 'ease-in-out' // CSS transition easing function 
    }
});



$(function() {
        isogroup = new Isogroup('.gallery-container');
});

