// Page-specific JS: Envelope Search page
;(function ($) {
    
    var feedback = "#feedback",
        output = "#out",
        recipient_stop_list = {},
        ac_source = [], // ac == AutoComplete. Docs http://api.jqueryui.com/autocomplete/
            // Each ac item = {  // See https://jqueryui.com/autocomplete/#custom-data
            //  value:  // an envelope_id
            //  label:  // a field from the envelope that we want to do auto-complete on
            // }
            // Each envelope has multiple items in the ac_source array, one for each
            // autocomplete lookup term
        ac_input_el = "#ac_input", // The short name of the envelope
        ac_envelope_id = false, // The id of the selected envelope
        envelope_display_el = "#envelope_display", // The selected envelope is displayed here
        db = false, // complete db from server. Augmented as we get data for additional envelopes
        db_by_envelope_id = false, // Enables lookup by envelope_id. See function build_lookup
            // This is an object. Envelope_id's are the keys. Each item is:
            // {
            //  i: the index for this envelope in the db
            //  desc: the description for this envelope for auto complete    
            // }
        steering_list = []; // The list of envelope_ids that we want to know about
        
    // db model:
    // {
    //     "account_id": "xxxxxxx-92b3-4a75-9331-xxxxxxx",
    //     "account_name": "NewCo",
    //     "envelopes": [],
    //     "err": false,
    //     "err_code": false,
    //     "latest_envelope_change": false,
    //     "oldest_envelope_change": false,
    //     "recipient_stop_list": {
    //         "email1@example.com": true
    //         "email2@example.com": true
    //     }
    // }
    
    function process_recipient(type, routing_order, name, email, envelope_id){
        // If appropriate, add a recipient to the autocomplete list.
        // You may want to update this function to fit your own autocomplete needs
        if (recipient_stop_list[email]) {
            return; // ignore any recipients in the stop list
        }
        add_to_autocomplete(name, envelope_id);
        add_to_autocomplete(email, envelope_id);
        // add_to_autocomplete(envelope_id, envelope_id); // lookup by envelope_id
        
        var parts = email.split('@');
        add_to_autocomplete(parts[1], envelope_id); // the email domain
        
        parts = name.split(' ');
        // A name may have more than two parts. Eg Input is Sam Spade Sr. We want search terms
        // Spade, Sam Sr. and Sr, Sam Spade. Sam Spade Jr is already taken care of
        
        
        
    }
    
    function add_to_autocomplete(term, envelope_id){
        ac_source.push({value: envelope_id, label: term})
    }
    
    function build_db(){
        // Creates subsidiary data and objects from the db
        build_lookup();
    }
    
    function build_lookup(){
        // Builds db_by_envelope_id
        db_by_envelope_id = {};
        db.envelopes.forEach(function(envelope, i, a){
            db_by_envelope_id[envelope.envelope_id] = {i: i};
        })
    }
    
    function lookup_by_envelope_id(envelope_id){
        if (db_by_envelope_id.hasOwnProperty(envelope_id)){ 
            return db.envelopes[db_by_envelope_id[envelope_id].i];
        } else {
            return false
        }
    }
            
    function lookup_i_by_envelope_id(envelope_id){
        if (db_by_envelope_id.hasOwnProperty(envelope_id)){
            return db_by_envelope_id[envelope_id].i;
        } else {
            return false
        }
    }

    var do_get_db = function _do_get_db(e){
        feedback = "#" + $(e.target).attr("data-feedback");
        $(feedback).text("Fetching database");
        $.ajax({
        url: "db?" + Date.now(), type: "GET",
        contentType: "application/json; charset=utf-8", dataType: "json"
        })
        .done(function (data, textStatus, jqXHR) {
            if (data.err && data.hasOwnProperty("err_code") && data.err_code === "PLEASE_AUTHENTICATE") {
                $(feedback).html("<b>Problem:</b> " + data.err + 
                " <a class='btn btn-primary' role='button' href='..'>Authenticate</a>");
            } else if (data.err && data.hasOwnProperty("err_code") && data.err_code === "PLEASE_REAUTHENTICATE") {
                $(feedback).html("<b>Problem:</b> Authentication has expired. Re-authentication in 3 seconds");
                var timer = window.setTimeout(function redirect(){window.location = data.redirect_url}, 3000);
            } else if (data.err) {
                    $(feedback).html("<b>Problem:</b> " + data.err);
            } else {
                db = data;
                build_db();
                recipient_stop_list = data.recipient_stop_list;
                envelope_update();
            }
        })
        .fail(function (jqXHR, textStatus, errorThrown) {
            $(feedback).html("<b>Problem:</b> " + textStatus);
        })
    }
    
    function envelope_update(){
        // Get envelope list, merge with db, retrieve data until API limit drops to under 500
        $(feedback).text("Fetching update information");
        do_get_envelope_list();
    }

    var do_get_envelope_list = function _do_get_envelope_list(){
        $.ajax({
        url: "update_envelope_list", type: "POST",
        contentType: "application/json; charset=utf-8", dataType: "json"
        })
        .done(function (data, textStatus, jqXHR) {
            if (data.err && data.hasOwnProperty("err_code") && data.err_code === "PLEASE_AUTHENTICATE") {
                $(feedback).html("<b>Problem:</b> " + data.err + 
                " <a class='btn btn-primary' role='button' href='..'>Authenticate</a>");
            } else if (data.err && data.hasOwnProperty("err_code") && data.err_code === "PLEASE_REAUTHENTICATE") {
                $(feedback).html("<b>Problem:</b> Authentication has expired. Re-authentication in 3 seconds");
                var timer = window.setTimeout(function redirect(){window.location = data.redirect_url}, 3000);
            } else if (data.err) {
                    $(feedback).html("<b>Problem:</b> " + data.err);
            } else {
                merge_envelope_list(data.envelopes);
            }
        })
        .fail(function (jqXHR, textStatus, errorThrown) {
            $(feedback).html("<b>Problem:</b> " + textStatus);
        })
    }
    
    function merge_envelope_list(envelopes){
        // Merge the incoming list with the database and get info where it's missing (up to limits)
        // Example input:
        // [
        //         {
        //             "envelope_id": "aaaaaaaa-e016-4df9-b595-66xxxxxxxx",
        //             "last_change": "2016-05-17T08:04:20.7600000Z",
        //             "status": "sent"
        //         },
        //         {
        //             "envelope_id": "aaaaaaaa-35c7-42d5-8a1f-07bxxxxxxxxx",
        //             "last_change": "2016-05-17T08:04:21.1230000Z",
        //             "status": "completed"
        //         },
        // ...
        // 
        $(feedback).text("Processing update information");
        envelopes.forEach(function _each_envelope(envelope, i, a){
            var envelope_id = envelope.envelope_id,
            i = lookup_i_by_envelope_id(envelope_id);
            
            if (i) {
                // Update existing entry in db
                db.envelopes[i].last_change = envelope.last_change;
                db.envelopes[i].status = envelope.status;
            } else{
                db.envelopes.push(envelope);
            }
        })
        build_db();
        create_steering_list();
        process_steering_list();
    }
    
    function create_steering_list(){
        // Create the steering_list -- envelope_ids that do not have additional info
        db.envelopes.forEach(function(envelope, i, a){
            if (! envelope.hasOwnProperty('recipients')) {
                steering_list.push(envelope.envelope_id);
            }
        })
    } 
    
    function process_steering_list(){
        var api_calls_remaining = 1000,  // from header X-RateLimit-Remaining → 996
            min_api_calls_remaining = 500,
            goal = steering_list.length;
            
        do_call();
        
        function do_call() {
            if (steering_list.length == 0){
                $(feedback).text("Finished fetching envelope info!");
                process_db();
                return;
            }
            if (api_calls_remaining < min_api_calls_remaining) {
                $(feedback).text("Stopping due to API limits. " + steering_list.length +
                    " envelopes remain. You can restart in an hour.");
                process_db();
                return;
            }             

            var envelope_id = steering_list.pop(),
                left = steering_list.length;            
            $(feedback).text("Fetching envelope info " + (0 + goal - left) + " of " + goal + "...");
            
            var data = {envelope_ids: [envelope_id]};
            $.ajax({
                url: "update_envelopes_list", type: "POST", data: JSON.stringify(data),
            contentType: "application/json; charset=utf-8", dataType: "json"
            })
            .done(function (data, textStatus, jqXHR) {
                if (data.err && data.hasOwnProperty("err_code") && data.err_code === "PLEASE_AUTHENTICATE") {
                    $(feedback).html("<b>Problem:</b> " + data.err + 
                    " <a class='btn btn-primary' role='button' href='..'>Authenticate</a>");
                } else if (data.err && data.hasOwnProperty("err_code") && data.err_code === "PLEASE_REAUTHENTICATE") {
                    $(feedback).html("<b>Problem:</b> Authentication has expired. Re-authentication in 3 seconds");
                    var timer = window.setTimeout(function redirect(){window.location = data.redirect_url}, 3000);
                } else if (data.err) {
                        $(feedback).html("<b>Problem:</b> " + data.err);
                } else {
                    if (data.statistics.rate_limit_remaining) {
                        api_calls_remaining = data.statistics.rate_limit_remaining;                        
                    }
                    process_envelope_update(data);
                    do_call(); // Call ourselves
                }
            })
            .fail(function (jqXHR, textStatus, errorThrown) {
                $(feedback).html("<b>Problem:</b> " + textStatus);
            })   
        }
    }
    
    function process_envelope_update(data){
        var incoming_fields = ["recipients", "custom_fields"];
        
        data.envelopes.forEach(function(envelope, i, a){
            var db_index = lookup_i_by_envelope_id(envelope.envelope_id);
            if (db_index) {
                incoming_fields.forEach(function(field, i, a){
                    db.envelopes[db_index][field] = envelope[field]})
            }
        })
    }

    function process_db(){
        // Processes the database for the AutoComplete
        $(feedback).text("Processing envelope data...");
        
        // Add each 
        
        
        $(feedback).text("Processing complete!");
    }

	
    function add_search_page_listeners(){
        // Page-specific JS: Envelope Search page   
        $('#get_db').click(do_get_db);
    }
    
    
    //////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	  
	// the mainline
	$(document).ready(function() {
        if ($(".envelope_search").length == 0) {
            return;
        }
        add_search_page_listeners();
	});
	
}(jQuery));

//////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////

// Array.foreach polyfill
Array.prototype.forEach||(Array.prototype.forEach=function(r,t){var o,n;if(null==this)throw new TypeError(" this is null or not defined");var e=Object(this),i=e.length>>>0;if("function"!=typeof r)throw new TypeError(r+" is not a function");for(arguments.length>1&&(o=t),n=0;i>n;){var a;n in e&&(a=e[n],r.call(o,a,n,e)),n++}});
// Array.find polyfill
Array.prototype.find||(Array.prototype.find=function(r){if(null===this)throw new TypeError("Array.prototype.find called on null or undefined");if("function"!=typeof r)throw new TypeError("predicate must be a function");for(var t,n=Object(this),e=n.length>>>0,o=arguments[1],i=0;e>i;i++)if(t=n[i],r.call(o,t,i,n))return t});
// Array.includes polyfill
Array.prototype.includes||(Array.prototype.includes=function(r){"use strict";var t=Object(this),e=parseInt(t.length)||0;if(0===e)return!1;var n,a=parseInt(arguments[1])||0;a>=0?n=a:(n=e+a,0>n&&(n=0));for(var s;e>n;){if(s=t[n],r===s||r!==r&&s!==s)return!0;n++}return!1});


