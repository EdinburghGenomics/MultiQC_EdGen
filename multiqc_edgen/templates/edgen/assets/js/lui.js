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

        // If the div is hidden then we'll bail out
        if (browser_div.is(':hidden')) {
            console.log("Skipping LUI as div is hidden");
            return;
        }
        console.log("Looking at run " + lui_runid  + " lane " + lui_lane);

        // If we're not on the web server this isn't going to work
        if (window.location.protocol != 'https:') return;

        // Load the infos for all the lanes.
        lui_endpoint = window.location.origin + '/lims_run_info/v1/run/';

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
        // <div style='padding: 2px 0px 10px 2px'>Lane-usable flag in clarity: <b style='padding-left: 6px'>Yes</b>
        //      <button style='float: right; min-width: 100px;'>Edit</button></div>
        //      <pre>Here is some preformatted text</pre>
        if(laneid == lui_lane){

            var lui_html = "<div style='padding: 2px 0px 10px 2px'>Lane-usable flag in clarity: ";
            lui_html += "<b style='padding-left: 6px'>" + lui_tr(infos["Lane QC"]) + "</b>";
            lui_html += "<button style='float: right; min-width: 100px;'>Edit</button></div>";
            if(infos["Fail Details"]){
                // Fail Details can now be any report we like. Add the text later in order to escape it.
                lui_html += "<pre>...</pre>";
            }

            browser_div.find("div#page_browser_lui").html(lui_html);
            browser_div.find("div#page_browser_lui").find("pre").text(infos["Fail Details"]);
            browser_div.find("div#page_browser_lui").attr("class", "lui_state_" + infos["Lane QC"]);

            browser_div.find("div#page_browser_lui button").click(function(e){
                e.preventDefault();
                // The callback here bakes in the browser_div and takes the JSON created by lui_put_a_flag,
                // then calls back to this function to show the new status.
                lui_prompt_flag( browser_div,
                                 function(new_json_data){ lui_show_flags(browser_div, new_json_data) },
                                 function(new_json_data){ lui_no_flags(browser_div, 'save') } );
            } );

            browser_div.find("div#page_browser_lui").fadeIn();

            // Also set the side bar colour
            $('.side-nav-wrapper').removeClass(
                            "lui_state_true lui_state_false lui_state_null").addClass(
                            "lui_state_" + infos["Lane QC"]);

            // Add in the hidden dialog ready to prompt the user for new values.
            // Remember that running the .dialog() function on this will remove it from the parent div so we need to
            // keep a handle on it.
            if( ! browser_div.lui_dialog ){
                // Make the dialog just-in-time (initially invisible)
                browser_div.append(
                    '<div id="lui_dialog" style="display: none" title="Is lane ' + lui_lane.substr(4) + ' usable?">' +
                     '<div style="clear: both;"><span id="lui_usable_label">Usable?</span> <span style="float: right;">' +
                     '<input type="radio" name="flag" id="flag_yes" style="margin: 4px"><label for="flag_yes">Yes</label>' +
                     '<input type="radio" name="flag" id="flag_no" style="margin: 4px"><label for="flag_no">No</label>' +
                     '</span></div><div>' +
                     'Remarks: <div><textarea name="blurb" style="width: 100%" cols="60" rows="4"></textarea></div>' +
                     '<div class="dialog_buttons" style="text-align: right">' +
                     '<button name="cancel" style="min-width: 80px">Cancel</button><button name="ok" style="min-width: 80px">OK</button>' +
                     '</div></div></div>');
                browser_div.lui_dialog = browser_div.find("div#lui_dialog");
            }

            // Insert the current state into the dialog box
            var lui_dialog = browser_div.lui_dialog;

            // As per by the LIMS, initial value is tri-state but once set can't be cleared.
            lui_dialog.find("input#flag_yes").prop("checked", (infos["Lane QC"] === true));
            lui_dialog.find("input#flag_no").prop("checked", (infos["Lane QC"] === false));

            lui_dialog.find("textarea[name='blurb']").val(infos["Fail Details"]);
        }
    }

}

function lui_prompt_flag(browser_div, ui_update_callback, ui_error_callback){
    /** Prompt the user to set the usable flag for the current lane
        In the first cut we were enforcing that an unusable lane must have a reason and a
        reason implies the lane is not usable, but this is not enforced anywhere else so
        could easily change!
    */
    var button_clicked = browser_div.find("div#page_browser_lui button");
    button_clicked.attr("disabled", true);

    /* The original version just popped up a generic prompt.
    var response = window.prompt("Click OK to set " + lui_lane + " usable, or enter a reason to mark it as failed.","");
    if( ! (response === null) ){
        button_clicked.text("Saving flag...");
        button_clicked.attr("disabled", true);

        lui_put_a_flag(lui_runid, lui_lane, !(response), response, ui_update_callback, ui_error_callback);
    }*/

    /* Now we want to use a more sophisticated dialog box. jquery-ui provides one. The dialog
     * was alredy set up above. */

    var dialog_div = browser_div.lui_dialog;

    if(dialog_div.hasClass("ui-dialog-content")){
        // The dialog is already set up. Just show it.
        dialog_div.dialog("open");
    }
    else
    {
        // Set it up
        browser_div.lui_dialog = dialog_div.dialog( { width: 500,
                                                      title: dialog_div.attr('title'),
                                                      appendTo: browser_div,
                                                    } );
        dialog_div = browser_div.lui_dialog;
        // To get the height auto-sizing we have to use a callback
        // Width sizing 'just works' so leave that to CSS.
        var size_difference = 0;
        var ta = dialog_div.find('textarea');
        dialog_div.bind("dialogresize", function(event, ui){
            if(! size_difference){
                size_difference = ui.originalSize.height - ta.height();
            }

            var new_height = ui.size.height - size_difference;

            if( new_height > 20 ){
                ta.css({height: new_height});
                dialog_div.css({height: 'auto', width: 'auto'});
            }
        });
        // And for some reason I have to do this manually? Something odd with the JS in MultiQC.
        $("button.ui-dialog-titlebar-close").addClass("ui-button-icon ui-icon ui-icon-closethick");

        dialog_div.find("button[name='cancel']").click( function(e){
                dialog_div.dialog("close");
        } );

	}

    // Now bind the buttons...
	// Do this on each showing so Cancel can properly reset the dialog state.
	// For consistency, closing the dialog should do the same
	var old_state = { check1: dialog_div.find("input#flag_yes").prop("checked"),
                      check2: dialog_div.find("input#flag_no").prop("checked"),
                      blurb:  dialog_div.find("textarea[name='blurb']").val(),
                      reset:  true};

    dialog_div.unbind("dialogclose");
	dialog_div.bind("dialogclose", function(e, ui){
            if(old_state['reset']){
                dialog_div.find("input#flag_yes").prop("checked", old_state['check1']);
                dialog_div.find("input#flag_no").prop("checked", old_state['check2']);
                dialog_div.find("textarea[name='blurb']").val(old_state['blurb']);

                button_clicked.attr("disabled", false);
            }
	});

    dialog_div.find("button[name='ok']").off("click");
	dialog_div.find("button[name='ok']").click( function(e){
		if( ! ( dialog_div.find("input#flag_yes").prop("checked") ||
                dialog_div.find("input#flag_no").prop("checked") ) ){
			// Well, which is it??
			var lui_usable_label = dialog_div.find("#lui_usable_label");
			lui_usable_label.text(lui_usable_label.text() + '?');
			lui_usable_label.css('font-weight', parseInt(lui_usable_label.css('font-weight')) + 200 );
			lui_usable_label.css('font-size', parseInt(lui_usable_label.css('font-size')) + 1 + 'px' );
		}
		else
		{
        	lui_put_a_flag( lui_runid, lui_lane,
							dialog_div.find("input#flag_yes").prop("checked"),
						 	dialog_div.find("textarea[name='blurb']").val(),
							ui_update_callback, ui_error_callback );
			old_state['reset'] = false;
			// The button will be re-enabled by the callback after AJAX.
        	button_clicked.text("Saving to the LIMS...");
            dialog_div.dialog("close");
		}
	} );

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

if(typeof internal_mode_flag !== 'undefined' && Boolean(internal_mode_flag)){
    $(document).ready(lui_setup);
}
