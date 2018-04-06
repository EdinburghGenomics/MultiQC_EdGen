/* Animate any apng elements found.
 * These should have class="apng_slider" and apng_data="<data>" where <data> is the
 * apng file in base64 format.
 */
function sliderize(div_elem) {
  //Load up the APNG image...
  var apng_frames = parseAPNG(
        new Uint8Array(atob(div_elem.attr('apng_data')).split("").map(function(c) {
            return c.charCodeAt(0); })) );

  //Use a closure to identify the player (when we get it)
  var player_handle = [];

  //Allow the label on the slider to be specified
  var slider_label = div_elem.attr('slider_label') || 'Frame to show';
  var zero_image = "Base"; // FIXME - this should be optional

  //Add the required elements into the div
  div_elem.html('<canvas width="100" height="100" style="padding-left: 50px"></canvas>' +
                '<div style="width: 90%">' +
                '<div style="padding: 6px; width: 100%">' +
                '<label for="frame_select">' + slider_label + '</label>' +
                '<select name="frame_select" id="frame_select" style="margin-left: 8px">' +
                ( zero_image ? '<option label="' + zero_image + '">0</option>' : '') +
                '</select></div><div id="frame_slider"></div></div>'
               )

  //Meld the slider and the selector, setting the range to the number of frames
  //in the APNG.
  div_elem.find("#frame_slider").slider({
      min: (zero_image ? 0 : 1),
      max: apng_frames.frames.length - (zero_image ? 1 : 0),
      range: "min",
      value: div_elem.find("#frame_select")[0].selectedIndex,
      slide: function(event, ui) {
        div_elem.find("#frame_select")[0].selectedIndex = ui.value;
        frame_change(div_elem.find("#frame_select")[0].selectedIndex, player_handle);
      }
    });
  div_elem.find("#frame_select").on("change", function() {
    div_elem.find("#frame_slider").slider("value", this.selectedIndex);

    frame_change(this.selectedIndex, player_handle);
  });

  //Add items to the selector list to match the slider.
  var fs = div_elem.find("#frame_select")[0]
  while(fs.length > apng_frames.frames.length){
    fs.options.remove(fs.options.length - 1)
  }
  while(fs.length < apng_frames.frames.length){
    var opt = document.createElement('option');
    opt.text = String(fs.length);
    fs.add(opt, null)
  }

  // Fix the canvas size based on the first frame size.
  div_elem.find("canvas").attr("width", apng_frames.frames[0].width);
  div_elem.find("canvas").attr("height", apng_frames.frames[0].height);

  //And play it
  apng_frames.getPlayer(div_elem.find("canvas").get()[0].getContext("2d"), false).then(
    function(p){ player_handle[0] = p } );
};

function frame_change(n, player_handle){
    //My understanding is that we can't just tell the player to go to
    //an arbitrary frame, but we can render all the frames to HTMLImageElements
    //and then flip through those. I think.

    if(! player_handle){
        console.log("Player not yet initialized.");
        return;
    }
    /*
    // Try 1 - pushing the player through the frames...
    console.log("Frame was " + player_handle[0].currentFrameNumber);

    if(player_handle[0].currentFrameNumber > n){
        player_handle[0].stop()
    }
    while(player_handle[0].currentFrameNumber != n){
        player_handle[0].renderNextFrame();
        if(player_handle[0].currentFrameNumber == 0){
            //We looped around!
            console.log("Frame " + n + "is out of range")
            return;
        }
    }
    */
    // Try 2 - fuxing the code to render a frame by number.
    // But this could corrupt the image as we can only get a frame correct by rendering it over
    // the previous version. May work for our use case, though!

    player_handle[0].renderFrame(n);

    console.log("Frame is now " + player_handle[0].currentFrameNumber);
}

$( function(){
    $(".apng_slider").each( function(){ sliderize( $(this) ) } );
});
