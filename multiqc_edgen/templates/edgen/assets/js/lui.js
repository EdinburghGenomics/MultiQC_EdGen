/* LUI == Lane Usability Indicator, as read from the Clarity LIMS */
function lui_setup(){
    // This show it actually runs.
    //window.prompt("Do you think this will work OK?", "No!!!");

    /* Move the disabling of tabs into CSS. The Python code will set div class to "page_browser_overview" or
     * "page_browser_full" and then a CSS hint can make them un-click-able.
     * Then JS will do the rest.
     *
     * Only for page_browser_full it will trigger an AJAX query for all lanes.
     * Then it will set the tab classes (and thus the colours) eg. "active lui_true" and also tweak the
     * class of the message div and the side div (which is $("div.side-nav"))
     *
     * How shall the JS know which lane it is dealing with? Maybe add it to the class of the page browser div,
     * so "page_browser_full lane1" and the tabs get id="nav_tab_lane1" etc. Actually just the latter will do,
     * though I'm now conflating the UI and the functionality quite a bit. This tends to happen in JS!
     */

    $('#page_browser.page_browser_full').each(function(){
        // Find the active tab to see what lane I am looking at
        var run_element = $(this)
        var runid = run_element.attr("runid");
        console.log("Looking at run " + runid);

        // Load the infos for all the lanes. Do I want to determine the endpoint like
        // this or do I want to hard-code it to web1?
        //var lri_endpoint = 'http://' + window.location.host + ':8002/v1/run/'
        var lri_endpoint = 'http://web1.genepool.private:8002/v1/run/'

        $.ajax({
            url: lri_endpoint + runid + '/flags',
            type: 'GET',
            dataType: "json",
            xhrFields: { withCredentials: true },
            success: function(d){ lui_show_flags(run_element, d)},
            error: function(){ lui_no_flags('load', run_element)},
        });
    });
}

function lui_tr(in_val){
    // Translate the QC state
    if(in_val === true){
        return 'Yes';
    }
    else if(in_val === false){
        return 'No';
    }
    else if(in_val === null){
        return 'Not Set';
    }
    return in_val;
}


function lui_show_flags(browser_div, json_data){
    // Set the tab style for all tabs
    // Looping through a dict in javascript is annoying.
    var active_lane = browser_div.find("li.active").attr('id').substring(8);
    var runid = browser_div.attr("runid");
    console.log("Selected lane is " + active_lane);

    var json_keys = Object.keys(json_data);
    for(var idx in json_keys) {
        var laneid = json_keys[idx];
        var infos = json_data[laneid];

        // Set the tab colours to say which lanes are usable or not, by setting
        // the class to "lui_state true" etc.
        browser_div.find("li#nav_tab_" + laneid).addClass("lui_state_" + infos["Lane QC"]);

        // Set the content of page_browser_lui and fade it in
        if(laneid == active_lane){

            var button_text = lui_tr(infos["Lane QC"])
            if(infos["Fail Details"]){
                button_text += " -- " + infos["Fail Details"]
            }

            browser_div.find("div#page_browser_lui").html('<span>Lane-usable flag in Clarity: <button>x</button></span>');
            browser_div.find("div#page_browser_lui").attr("class", "lui_state_" + infos["Lane QC"]);

            browser_div.find("div#page_browser_lui button").text(button_text);
            browser_div.find("div#page_browser_lui button").click({runid: runid, lane: laneid}, function(e){
                e.preventDefault();
                lui_prompt_flag(e.data.runid, e.data.lane, null);
            } );

            browser_div.find("div#page_browser_lui").fadeIn();

            // Also set the side bar
            $('.side-nav-wrapper').addClass("lui_state_" + infos["Lane QC"]);
        }
    }

}

function lui_prompt_flag(runid, laneid, ui_update_callback){
    /** Prompt the user to set the usable flag for the lane
        Here we're enforcing that an unusable lane must have a reason and a
        reason implies the lane is not usable, but this is not enforced anywhere else so
        could easily change!
    */
    response = window.prompt("Click OK to set " + laneid + " usable, or enter a reason to mark it as failed.","");
    if( ! (response === null) ){
        put_a_flag(runid, laneid, !(response), response, gui_update_callback);
    }
}

function lui_no_flags(whatever, browser_div){
    // TODO - something more better that actually shows the state in the GUI
    var my_msg = ("Failed to " + whatever + " flags for run <em>" + browser_div.attr("runid") + "</em>" );

    browser_div.find("div#page_browser_lui").html('<span>' + my_msg + '</span>');
    browser_div.find("div#page_browser_lui").fadeIn();
}

$(document).ready(lui_setup);
