// Javascript for API logging

;(function ($) {
  
	// Private global variabls for the functions
	var toc_items = [], // array of the notification items that are being displayed
		ace_editors = {request: false, response: false},
        ace_cdn = "https://cdnjs.cloudflare.com/ajax/libs/ace/1.2.3/", // Where ACE loads optional JS from
        omit_base64_text = "[Base64 data omitted]",
        omit_image_text  = "[Image data omitted]",
        item_intro_template,
        request_tab_template,
        response_tab_template;
            
    // FORMAT OF THE TOC ENTRIES
    // toc_entries is an array. The element [0] is the oldest, shown at the bottom of the page.
    // Each entry is {
    //    success: boolean -- was the call successful?
    //    url: the url for retrieving the call
    //    file_name: the raw file_name. Can be used for sorting the entries
    //    x_ray: false if no x_ray header. Otherwise the contents of the header
    //    method: GET, POST, etc
    //    request_url: the complete request url
    //    method_name: the method name used in the log file name
    //    body: the NOT uuencoded first 1500 bytes of the log entry
    //    date_time: the call was made before this time
    // }
	
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////

    // Page-specific JS: API Logging page
    function add_API_Logs_page_listeners() {
        // Add listener for the logging-status-refresh
        //     ... logging status: <span id="logging-status">tbd</span><span></span><a href="#" id="logging-status-refresh">Refesh<
        $('#logging-status-refresh').click(logging_status);
        logging_status(); // Run it once pro-actively on page load

        // Add listener for download
        // <button type="button" class="btn btn-primary marginleft" id="logging-download" data-feedback="feedback-download">Download Logs</button>
        var feedback = $('#logging-download').attr("data-feedback");
        $('#logging-download').click(feedback, logs_download);
    }
    
    var logging_status = function _logging_status(e) {
        var logging_status = $("#logging-status"),
            counter_el = $(logging_status).next()[0],
            countdown_i,
            countdown = function () {
                countdown_i -= 1;
                $(counter_el).text(countdown_i)
            },
            countdown_id;

        $(logging_status).text("Working... ");
        countdown_i = 100;
        countdown_id = setInterval(countdown, 300);
        $.ajax({
            url: "logging_status?" + Date.now(), type: "GET",
            contentType: "application/json; charset=utf-8", dataType: "json"
        })
            .done(function (data, textStatus, jqXHR) {
                if (data.err && data.hasOwnProperty("err_code") && data.err_code === "PLEASE_AUTHENTICATE") {
                    $(logging_status).html("<b>Problem:</b> " + data.err + 
                    " <a class='btn btn-primary' role='button' href='..'>Authenticate</a>");
                } else if (data.err && data.hasOwnProperty("err_code") && data.err_code === "PLEASE_REAUTHENTICATE") {
                    $(logging_status).html("<b>Problem:</b> Authentication has expired. Re-authentication in 3 seconds");
                    var timer = window.setTimeout(function redirect(){window.location = data.redirect_url}, 3000);
                } else if (data.err) {
                        $(logging_status).html("<b>Problem:</b> " + data.err);
                } else {
                    $(logging_status).html(data.status);
                }
            })
            .fail(function (jqXHR, textStatus, errorThrown) {
                $(logging_status).html("<b>Problem:</b> " + textStatus);
            })
            .always(function () {
                clearInterval(countdown_id);
                $(counter_el).text("")
            });
    }
    
    var logs_download = function _logs_download(e){
        var feedback = e.data,
            feedback_el = $("#" + feedback),
            counter_el = $(feedback_el).next()[0],
            countdown_i,
            countdown = function(){countdown_i -= 1; $(counter_el).text(countdown_i)},
            countdown_id,
            stop_feedback = function(){$(feedback_el).html("");clearInterval(countdown_id); $(counter_el).text("");};

        $(feedback_el).text("Working... ");
        countdown_i = 100; countdown_id = setInterval(countdown, 300);
        $.ajax({
            url: "logs_download", type: "POST",
            contentType: "application/json; charset=utf-8", dataType: "json"})
            .done(function(data, textStatus, jqXHR) {
                if (data.err) {
                    stop_feedback();
                    if (data.hasOwnProperty('err_code') && data.err_code === 404) {
                        $(feedback_el).html("No logging entries to download.");
                        window.setTimeout(function(){$(feedback_el).html("")}, 8000);
                    } else if (data.hasOwnProperty("err_code") && data.err_code === "PLEASE_REAUTHENTICATE") {
                        $(feedback_el).html("<b>Problem:</b> Authentication has expired. Re-authentication in 3 seconds");
                        var timer = window.setTimeout(function redirect(){window.location = data.redirect_url}, 3000);
                    } else {
                        $(feedback_el).html("<b>Problem:</b> " + data.err);
                    }
                } else {
                    stop_feedback();
                    $(feedback_el).html("<b>Processing...</b>");
                    process_new_items(data, stop_feedback, true);
                }
            })
            .fail(function(jqXHR, textStatus, errorThrown) {
                stop_feedback();
                $(feedback_el).html("<b>Problem:</b> " + textStatus);
            })
            .always(function(){window.setTimeout(logging_status, 0)
            })
    }
    
    function logs_initial_download(){
        // Do the initial download of log entries that were already on the server 
        // (not DocuSign platform)
        var feedback = "working",
            feedback_el = $("#" + feedback),
        stop_feedback = function(){$(feedback_el).html("")};
        $(feedback_el).text("Fetching... ");
        $.ajax({
            url: "logs_list" + "?" + Date.now(), type: "GET",
            contentType: "application/json; charset=utf-8", dataType: "json"})
            .done(function(data, textStatus, jqXHR) {
                if (data.err && data.hasOwnProperty("err_code") && data.err_code === "PLEASE_REAUTHENTICATE") {
                    $(feedback_el).html("<b>Problem:</b> Authentication has expired. Re-authentication in 3 seconds");
                    var timer = window.setTimeout(function redirect(){window.location = data.redirect_url}, 3000);
                } else if (data.err) {
                    stop_feedback();
                    $(feedback_el).html("<b>Problem:</b> " + data.err);
                } else {
                    $(feedback_el).html("Processing...");
                    window.setTimeout(process_new_items, 0, data, stop_feedback, false);
                }
            })
            .fail(function(jqXHR, textStatus, errorThrown) {
                stop_feedback();
                $(feedback_el).html("<b>Problem:</b> " + textStatus);
            });
    }


	function process_new_items(data, stop_feedback, animate){
		// Process the list of items
		// The data is an array of raw log entries format:
		// { file_name: "T2016-07-17T13_51_07__00_OK_GetAccountSharedAccess.txt"
        //   head: base64 version of first 1500 char of the log file
        //   url: url for retrieving the complete file
		// }
        //
        // 
        data = data.entries;
		if (data.length == 0) {
            stop_feedback(); // nothing to do...
            return;
        } 

		// Sort the incoming events so the newest (_00) is first.
		data.sort(function (a, b) {
			return (a.file_name > b.file_name) ? -1 : 1; // compare the file names
        });

        // process each new entry
		data.forEach (function(val, index, arr){add_to_toc(examine(val), animate)});
        stop_feedback();
    }
	
    function examine(item){
        // Compute the item's information
        //    success: boolean -- was the call successful?
        //    url: the url for retrieving the call
        //    file_name: the raw file_name. Can be used for sorting the entries
        //    x_ray: false if no x_ray header. Otherwise the contents of the header
        //    method: GET, POST, etc
        //    request_url: the complete request url
        //    method_name: the method name used in the log file name
        //    head: the NOT uuencoded first 1500 bytes of the log entry
        //    date_time: the call was made before this time

        item.head = window.atob(item.head);
   		//  file_name: "T2016-07-17T13_51_07__00_OK_GetAccountSharedAccess.txt"

        var // See https://regex101.com/#javascript for testing
            re_success = /(_OK_)|(_Created_)/,
            success = re_success.test(item.file_name),
            re_x_ray = /\nX\-ray: (.*)\n/m,
            re_x_ray_r = re_x_ray.exec(item.head),
            x_ray = re_x_ray_r ? re_x_ray_r[1] : false,
            re_method_url = /^([A-Z]*) (.*)/,
            re_method_url_r = re_method_url.exec(item.head),
            method = re_method_url_r ? re_method_url_r[1] : false,
            request_url = re_method_url_r ? re_method_url_r[2] : false,
            re_time_method = /T(\w*-\w*-\w*_\w*_\w*)__\w*_(\w*)/,
            re_time_method_r = re_time_method.exec(item.file_name),
            method_name = re_time_method_r ? re_time_method_r[2] : false,
            date_time = re_time_method_r ? re_time_method_r[2].replace("_", ":").replace("T", " ") : false;
        
        item.success = success;
        item.x_ray = x_ray;
        item.method = method;
        item.request_url = request_url;
        item.method_name = method_name;
        item.date_time = date_time;
        return item;
    }

	function add_to_toc(item, animate){
        // Set css class depending on success field
        item.css_class = item.success ? "success-circle" : "failure-circle";
        
		toc_items.push(item); // We're assuming that we won't receive an item out of order.
		// Create the new li by using mustache with the template
	    var rendered = Mustache.render($('#toc_item_template').html(), item);
		prependListItem("toc", rendered, animate);
		// The new item is now the first item in the toc ul.
		$("#toc").children().first().click(item, show_item).tooltip(); // See http://getbootstrap.com/javascript/#tooltips
	}
	
	function prependListItem(listName, listItemHTML, animate){
		// See http://stackoverflow.com/a/1851486/64904
	    if (animate) {
            $(listItemHTML)
                .hide()
                .css('opacity',0.0)
                .prependTo('#' + listName)
                .slideDown('slow')
                .animate({opacity: 1.0});
        } else {
            $(listItemHTML).prependTo('#' + listName);
        }
		window_resized();
	}

	var show_item = function(event) {
		// This is a jQuery event handler. See http://api.jquery.com/Types/#Event
		// It fills in the main column
		var item = event.data, // our object about the log entry
			item_info_el = $("#item-feedback");
	
		$(item_info_el).html("<h2>Working...</h2>").show();
		$.ajax({url: item.url, type: 'get'})
		    .fail(function(jqXHR, textStatus, errorThrown) {
		        $(item_info_el).html(
                    "<h3>Problem: Couldn’t fetch the file</h3><p>URL: " + item.url + "</p><p>Status: " + textStatus + "</p>");
		        })
		    .done(function(data, textStatus, jqXHR){do_show_item(data, textStatus, jqXHR, item); $(item_info_el).hide()})
	}

    var do_show_item = function(data, textStatus, jqXHR, item) {
        
        var parsed, omit_base64;
        // Parse the item into parsed: {
        //   raw
        //   request: {
        //      method
        //      method_name: // from name of log file
        //      date_time:   // request was before this time
        //      url
        //      headers
        //      content_type
        //      content_type_json: boolean // is the request content-type JSON?
        //      content_type_multipart: boolean
        //      json_problem: false or an error message // Does the JSON parse?
        //      body
        //      show_editor
        //      json // the request, parsed into a json object (iff json_ok)
        //   response: {
        //      success:  // boolean, a successful request?
        //      success_class = success ? "success-circle" : "failure-circle"
        //      status:   // eg "201 Created"
        //      headers
        //      content_type
        //      content_type_json: boolean // is the response content-type JSON?
        //      content_type_multipart: boolean
        //      json_problem: false or an error message // Does the JSON parse?
        //      body
        //      show_editor
        //      json // the response, parsed into a json object (iff json_ok)
        
        function parse_it(){
            var raw = data,
                re_cr_style = /\r\n\r\n/m,
                cr_style = re_cr_style.test(raw), // Does the file use \r\n as line endings?
                eol = cr_style ? "\r\n" : "\n",
                eol_size = eol.length,
                end_of_line1 = raw.indexOf(eol),
                line1 = raw.substring(0, end_of_line1).replace("\r\n", "\n");
                    
            parsed = {
                raw: data,
                request:{
                    method: item.method,
                    method_name: item.method_name,
                    date_time: item.date_time
                },
                response: {
                    success: item.success,
                    success_class: item.success ? "success-circle" : "failure-circle"
            }};
            
            // First, treat the incoming data as one long string and change any
            // "documentBase64": "JVB blah blah" to 
            // "documentBase64": "[Base64 data omitted]" 
            if (omit_base64) {
                var re_omit64 = /"documentBase64":\s*"([^"]*)"/g;
                raw = raw.replace(re_omit64, '"documentBase64":"' + omit_base64_text +'"');
                
                var re_omit_images = /"imageBytes":\s*"([^"]*)"/g;
                raw = raw.replace(re_omit_images, '"imageBytes":"' + omit_image_text +'"');
            }
            
            parsed.request.url = line1.split(" ")[1];
            raw = raw.substring(end_of_line1 + eol_size); // remove first line
            var end_of_headers = raw.indexOf(eol + eol);
            parsed.request.headers = raw.substring(0, end_of_headers).replace("\r\n", "\n");
            raw = raw.substring(end_of_headers + eol_size * 2);  // Now raw starts at the beginning of the request body

            // Find the request Content-Type. Eg Content-Type: application/pdf
            // NB, the request may not have a content type!
            var ct = content_type(parsed.request.headers);
            parsed.request.content_type = ct;
            parsed.request.content_type_json = ct && ct === "application/json";
            parsed.request.content_type_multipart = ct && ct.includes("multipart");

            var re_status = /^\d{3} [A-Z][A-Za-z]{1,}$/m,
                end_of_req_body_index = raw.search(re_status);

            parsed.request.body = raw.substring(0, end_of_req_body_index);
            if (parsed.request.body === "" || parsed.request.body === eol) {parsed.request.body = false}
            parsed.request.show_editor = parsed.request.body !== false && !parsed.request.content_type_multipart;
            raw = raw.substring(end_of_req_body_index); // Now raw starts with the status line

            var cr_index = raw.indexOf(eol);
            parsed.response.status = raw.substring(0, cr_index);
            raw = raw.substring(cr_index + eol_size); // Now raw starts with the response headers
            end_of_headers = raw.indexOf(eol + eol);
            parsed.response.headers = raw.substring(0, end_of_headers).replace("\r\n", "\n");
            raw = raw.substring(end_of_headers + eol_size * 2);  // Now raw starts at the beginning of the response body

            // Find the response content type. Eg Content-Type: application/pdf
            ct = content_type(parsed.response.headers);
            parsed.response.content_type = ct;
            if (!ct) {
                // Very strange that the *response* doesn't have a content type. Assume it's json
                ct = "application/json"
            }
            parsed.response.content_type_json = ct === "application/json";
            parsed.response.content_type_multipart = ct.includes("multipart");
            parsed.response.body = raw;
            if (parsed.response.body === "" || parsed.response.body === eol) {parsed.response.body = false}
            parsed.response.show_editor = parsed.response.body !== false && !parsed.response.content_type_multipart;
            
            raw = null;

            // fill in json bodies with parse error check
            ["request", "response"].forEach(function(i){
                if (parsed[i].content_type_json){
                    parsed[i].json_problem = false;
                    try {
                        parsed[i].json = JSON.parse(parsed[i].body)
                    } catch (e) {
                        parsed[i].json_problem = "JSON parsing problem: " + e.message;
                    }
                }
            })
        }

        // THE MAIN STEM
        $("#item-wrapper").hide();
        omit_base64 = $("#omit-content").is(':checked');
        parse_it();
        $("#item-intro").html(item_intro_template(parsed));
        $("#request-tab").html(request_tab_template(parsed));
        $("#response-tab").html(response_tab_template(parsed));
        $("#raw-tab").html(parsed.raw);
        $("#raw_download").html("<a download='" + parsed.request.method_name + 
        ".txt' type='application/octet-stream'>Download the raw log entry</a>");
        var d = new Blob([parsed.raw]);
        $("#raw_download a").attr("href", URL.createObjectURL(d));
        
        // Add content to the editor windows as appropriate
        // Editors will be in 
        //   <div id="request-body-editor" class="log_editor"></div>                                
        //   <div id="response-body-editor" class="log_editor"></div>                                
        create_editors();
        ["request", "response"].forEach(function(i){
            if (parsed[i].show_editor) {            
                $("#" + i + "-body-editor").show();   
                var value = parsed[i].body;
                if (parsed[i].content_type_json && parsed[i].json_problem === false) {
                    value = JSON.stringify(parsed[i].json, null, 4);
                }
                ace_editors[i].setValue(value);
                ace_editors[i].getSelection().clearSelection();
                ace_editors[i].getSelection().moveCursorToScreen(0,0,true);
            } else {
                $("#" + i + "-body-editor").hide();
            }
        })
        $("#item-wrapper").show();
	}

    function create_editors(){
        if (ace_editors.request) {return}
        ace.config.set("workerPath", ace_cdn);

        ["request", "response"].forEach(function(i){
            ace_editors[i] = ace.edit(i + "-body-editor");
            ace_editors[i].setReadOnly(true);
            ace_editors[i].setTheme("ace/theme/chrome");
            ace_editors[i].setOption("wrap", "free");
            ace_editors[i].$blockScrolling = Infinity;
            window_resized();
            var XMLMode = ace.require("ace/mode/xml").Mode,
                JSONMode = ace.require("ace/mode/json").Mode,
            ace_session = ace_editors[i].getSession();
            // ace_session.setMode(new XMLMode());
            ace_session.setMode(new JSONMode());

            // ace_session.setMode("ace/mode/json");
            ace_session.setUseWrapMode(true);
            ace_session.setFoldStyle("markbeginend");
        })
    }

    function content_type(headers){
        // Get the content type, if present in the headers. The headers EOL is "\n"
        var re_content_type = /^Content-Type: (.*)/m,
            ct = re_content_type.exec(headers);
        if (! ct) {
            return false
        }
        ct = ct[1];
        // Handle if it looks like this: Content-Type: application/json; charset=utf-8
        ct = ct.split(";")[0]
        return ct;
    }

	var window_resized = function(){
		// resize left column
		var available = window.scrollHeight ? window.scrollHeight : $(window).height(),
			h = available -  $("#status_left").position().top; 
			// At least for Chrome, scrollHeight is only defined if there is a scrollbar
		
		// if ($(window).width() > 991) { $("#status_left").height(h); }
		
		// resize editor div, 300 min
		var min = 300;
		// if (ace_editor) {			
		// 	h = $(window).height() - $("#editor").offset().top - $(".navbar").height() - 5;
		// 	// The navbar is fixed so offset doesn't include it. (?)
        // 
		// 	$("#editor").height((h < min) ? min : h);
		// 	ace_editor.resize();
		// }
	}
    
    function set_tab_visible_handlers(){
        // Whenever a tab that has an editor in it becomes visible, we
        // need to call resize on the editor or its current data is not shown(!)
        
        $('a[data-refresh]').on('shown.bs.tab', function (e) {
            // e.target // newly activated tab
            // data-refresh=request
            var i = $(e.target).attr("data-refresh");
            ace_editors[i].resize();
        })
    }

	var countdown = function(){
		// Update the countdown value
		countdown_i -= 1;
		$("#counter").text(countdown_i);
	}
	
	function stop_countdown(){
		if (! countdown_interval_id) {return;}
		clearInterval(countdown_interval_id);
		countdown_interval_id = false;
		$("#countdown").hide();
		$("#xml_info").html("<h1 class='toc-instructions'>← Click an item to see the XML file</h1>");
	}
	
	function working_show(){
		$("#working").removeClass("workinghide").addClass("workingshow");
	}
	
	function working_hide(){
		$("#working").removeClass("workingshow").addClass("workinghide");
	}
	
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	
	function xml_make_pretty (xml) {
		// From https://gist.github.com/sente/1083506
		var formatted = '',
		    reg = /(>)(<)(\/*)/g,
			pad = 0,
			pad_content = "    ";
			
		xml = xml.replace(reg, '$1\r\n$2$3');

		jQuery.each(xml.split('\r\n'), function(index, node) {
		    var indent = 0;
		    if (node.match( /.+<\/\w[^>]*>$/ )) {
		        indent = 0;
		    } else if (node.match( /^<\/\w/ )) {
		        if (pad != 0) {
		            pad -= 1;
		        }
		    } else if (node.match( /^<\w[^>]*[^\/]>.*$/ )) {
		        indent = 1;
		    } else {
		        indent = 0;
		    }

		    var padding = '';
		    for (var i = 0; i < pad; i++) {
		        padding += pad_content;
		    }

		    formatted += padding + node + '\r\n';
		    pad += indent;
		});

		return formatted;
	}
	
	
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	  
	// the mainline
	$(document).ready(function() {
        if ($(".api_logs").length == 0) {
            return;
        }
        add_API_Logs_page_listeners();
        item_intro_template = Handlebars.compile($("#item-intro-template").html()); // Compile the templates once
        request_tab_template = Handlebars.compile($("#request-tab-template").html());
        response_tab_template = Handlebars.compile($("#response-tab-template").html());
        
        logs_initial_download();
	    window_resized();
        create_editors();
        set_tab_visible_handlers();
	    $(window).resize(window_resized);
	});
	
}(jQuery));

	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	//////////////////////////////////////////////////////////////////////////////
	///////////////////////////////////////////////////////////////////////////

// Polyfill for string.includes. See https://developer.mozilla.org/en/docs/Web/JavaScript/Reference/Global_Objects/String/includes
String.prototype.includes||(String.prototype.includes=function(t,e){"use strict";return"number"!=typeof e&&(e=0),e+t.length>this.length?!1:-1!==this.indexOf(t,e)});


