/* Un-hide the elements that we expect to see in our internal reports which are
 * hidden in the reports we send out to customers.
 *
 * This needs to be run before LUI, and it need to run synchronously so no checking
 * for the existence of other files can be used in our calculations. Instead
 * look to see if the filename starts with "multiqc_report_".
 */


function unhider(){

    var pathsplit = window.location.pathname.split('/');
    var filename = pathsplit.pop();

    if ( ! /^multiqc_report_/.test(filename) ) {
        console.log("Treating report as a stand-alone report.");
        return;
    }

    // The elements that want to be shown know that they want to be shown.
    $('.unhideme').each(function(){
       $(this).show();
    });

}

$(document).ready(unhider);
