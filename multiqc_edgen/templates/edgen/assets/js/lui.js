/* LUI == Lane Usability Indicator, as read from the Clarity LIMS */

// Global info set by setup. We assume there is only one indicator per page!
lui_endpoint = null;
lui_runid = null;
lui_lane = null;

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
        var browser_div = $(this);
        lui_runid = browser_div.attr("runid");
        lui_lane = browser_div.find("li.active").attr('id').substring(8);
        console.log("Looking at run " + lui_runid  + " lane " + lui_lane);

        // Load the infos for all the lanes. Do I want to determine the endpoint like
        // this or do I want to hard-code it to web1?
        //var lui_endpoint = 'http://' + window.location.host + ':8002/v1/run/'

        // If the user is viewing the report from ahost other than web1 they should see an
        // "unable to load" message as the CORS headers will not permit a log-in prompt.
        lui_endpoint = 'http://web1.genepool.private:8002/v1/run/';

        $.ajax({
            url: lui_endpoint + lui_runid + '/flags',
            type: 'GET',
            dataType: "json",
            xhrFields: { withCredentials: true },
            success: function(d){ lui_show_flags(browser_div, d)},
            error: function(){ lui_no_flags(browser_div, 'load')},
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
    /** Set the tab style for all tabs
     *  Looping through a dict in javascript is annoying.
     */

    var json_keys = Object.keys(json_data);
    for(var idx in json_keys) {
        var laneid = json_keys[idx];
        var infos = json_data[laneid];

        // Set the tab colours to say which lanes are usable or not, by setting
        // the class to "lui_state_true" etc.
        // Remove any previous state first
        browser_div.find("li#nav_tab_" + laneid).removeClass(
                                "lui_state_true lui_state_false lui_state_null").addClass(
                                "lui_state_" + infos["Lane QC"]);

        // Set the content of page_browser_lui and fade it in if not already visible.
        if(laneid == lui_lane){

            var button_text = lui_tr(infos["Lane QC"])
            if(infos["Fail Details"]){
                button_text += " -- " + infos["Fail Details"]
            }

            browser_div.find("div#page_browser_lui").html('<span>Lane-usable flag in Clarity: <button>x</button></span>');
            browser_div.find("div#page_browser_lui").attr("class", "lui_state_" + infos["Lane QC"]);

            browser_div.find("div#page_browser_lui button").text(button_text);
            browser_div.find("div#page_browser_lui button").click(function(e){
                e.preventDefault();
                // The callback here bakes in the browser_div and takes the JSON created by lui_put_a_flag,
                // then calls back to this function to show the new status.
                lui_prompt_flag( $(this),
                                 function(new_json_data){ lui_show_flags(browser_div, new_json_data) },
                                 function(new_json_data){ lui_no_flags(browser_div, 'save') } );
            } );

            browser_div.find("div#page_browser_lui").fadeIn();

            // Also set the side bar
            $('.side-nav-wrapper').removeClass(
                            "lui_state_true lui_state_false lui_state_null").addClass(
                            "lui_state_" + infos["Lane QC"]);
        }
    }

}

function lui_prompt_flag(button_clicked, ui_update_callback, ui_error_callback){
    /** Prompt the user to set the usable flag for the current lane
        Here we're enforcing that an unusable lane must have a reason and a
        reason implies the lane is not usable, but this is not enforced anywhere else so
        could easily change!
    */
    response = window.prompt("Click OK to set " + lui_lane + " usable, or enter a reason to mark it as failed.","");
    if( ! (response === null) ){
        button_clicked.text("Saving flag...");
        button_clicked.attr("disabled", true);

        lui_put_a_flag(lui_runid, lui_lane, !(response), response, ui_update_callback, ui_error_callback);
    }
}

function lui_put_a_flag(runid, lane, state, reason, ui_update_callback, ui_error_callback){
    /** Sends the JSON to the server. We'll only set one flag at a time.
    *   Broken out from lui_prompt_flag for ease of testing.
    *   Note this uses supplied run+lane, not the globals.
    */
    var json_payload = {};
    json_payload[lane] = {"Fail Details": reason, "Lane QC": state};

    // Set the setting and update the UI
    $.ajax({
        url: lui_endpoint + lui_runid + '/flags',
        type: "PUT",
        data: JSON.stringify(json_payload),
        dataType: "text", // Response is simply ignored if status is 200
        xhrFields: { withCredentials: true },
        success: function(d){ ui_update_callback(json_payload) },
        // Or else - make an explicit call to the server to confirm the setting.
        // Except there seems to be some delay from Clarity before I actually see the new value,
        // so this is suspect and I could only make it work with the arbitrary delay.
        /*
        success: function(){
            new Promise((resolve) => setTimeout(resolve, 1000)).then(() => {
                $.ajax({
                    url: lui_endpoint + runid + '/flags?lane=' + lane,
                    type: "GET",
                    dataType: "json",
                    xhrFields: { withCredentials: true },
                    success: function(json_returned){ ui_update_callback(json_returned) }
                });
            });
        }, */
        error: function(){ ui_error_callback() },
    });
}


function lui_no_flags(browser_div, action_type){
    // TODO - something more better that actually shows the state in the GUI
    var my_msg = ("Failed to " + action_type + " usable/unusable flags for run <em>" + lui_runid + "</em>" );

    browser_div.find("div#page_browser_lui").html('<span>' + my_msg + '</span>');
    browser_div.find("div#page_browser_lui").fadeIn();
}

$(document).ready(lui_setup);
