function initialise_previews(){
    let yOff = 60; // Horizontal position of image relative to mouse pointer.
    let xOff = 135; // Vertical position of image relative to mouse pointer
    $('.card_entry').mouseenter(function (e) {
        if ($(this).parent('div').children('div.hover_img').length === 0) {
            let image_url = $(this).data('image');
            console.log(image_url);
            let imageTag = '<div class="hover_img">' + '<img src="' + image_url +
                '"style="top: '+ (e.pageY - yOff) +'px; left: '+ (e.pageX + xOff) +'px;" ' +
                'alt="image" />' + '</div>';
            $(this).parent('div').append(imageTag);
        }
        $(this).parent('div').children('div.hover_img').show();
    });

    $('.card_entry').mouseleave(function () {
        $(this).parent('div').children('div.hover_img').hide();
    });
}