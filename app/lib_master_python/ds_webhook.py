# DocuSign webhook library
#
# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')
import os, base64, json, requests, logging
from app.lib_master_python import ds_salesforce
from app.lib_master_python import ds_recipe_lib
from app.lib_master_python import ds_cache
from flask import request, session
from bs4 import BeautifulSoup

webhook_path = "/webhook"
xml_file_dir = "app/static/files/"
doc_prefix = "doc_"
heroku_env = 'DYNO' # Used to detect if we're on Heroku
trace_value = "py_webhook" # Used for tracing API calls
trace_key = "X-ray"

########################################################################
########################################################################
#
# This module takes care of the session["webhook"] data.
# It stores:
#   enabled: True/False
#   status: {
#       yes: use the listener_url
#       no: User has told us to not use the webhook
#       ask: Ask the User what we should do.
#
#   listener_url: the complete listener url used by the DocuSign platform to send us notifications
#                 It must be accessible from the public internet
#   url_begin: the part of the path that might be changed
#   url_end: the last bit that won't change. Eg /webhook


def get_webhook_status():
    """Returns the webhook status of the current session

    Side-effect: initializes webhook setting

    Returns:
    webhook_status = {
        err: False or a problem string.
        status:
            yes: use the listener_url
            no: User has told us to not use the webhook
            ask: Ask the User what we should do.
        listener_url # The complete listener url that we're planning to use
        url_begin: the part of the path that might be changed
        url_end: the last bit that won't change. Eg /webhook

        }
    """

    if 'webhook' in session:
        webhook = session['webhook']
    else:
        webhook = webhook_default()
        session['webhook'] = webhook # Set it!

    return {
            'err': False,
            'status': webhook['status'],
            'url_begin': webhook['url_begin'],
            'url_end': webhook['url_end'],
            'listener_url': webhook['listener_url']
        }

def webhook_default():
    """Initialize the webook settings. For this app, we always need the webhook on... """

    webhook = {
        'enabled': False, # For this app, we just receive webhook data.
                          # The webhook subscription is started manually so we don't need the info
        'status': 'no',
        'url_begin': ds_recipe_lib.get_base_url(1),
        'url_end': webhook_path,
        'listener_url': False
    }
    return webhook

def set_webhook_status():
    """Enables the webhook status to be set for the session.

    The Request body:
    webhook_status, url_begin

    The Response:
    Same as from get_webhook_status
    """

    req = request.get_json()
    webhook_status = "yes" # constant since we always need to use the webhook in this app
    url_begin = req["url_begin"]

    if not (webhook_status=="no" or webhook_status == "yes"):
        return {"err": "Please select a webhook status"}
    if len(url_begin) < 7:
        return {"err": "Please enter a server address, including http or https"}

    webhook = {
        'enabled': webhook_status == "yes",
        'status': webhook_status,
        'url_begin': url_begin,
        'url_end': webhook_path,
        'listener_url': url_begin + webhook_path
    }
    session["webhook"] = webhook # Set it!

    return {
        'err': False,
        'status': webhook['status'],
        'url_begin': webhook['url_begin'],
        'url_end': webhook['url_end'],
        'listener_url': webhook['listener_url']
    }


########################################################################
########################################################################

def status_page():
    """Information for the status (notifications) page

    Returns:
        ds_params: JSON string format for use by the Javascript on the page.
            {status_envelope_id, url}  # url is the base url for this app
    """
    ds_params = json.dumps(
        {"url": ds_recipe_lib.get_base_url(1)})
    return {"ds_params": ds_params}

########################################################################
########################################################################

def status_items():
    """List of info about the envelope event items that were received"""
    auth = session["auth"]
    account_id = auth["account_id"]
    files_dir_url = ds_recipe_lib.get_base_url(2) + "/static/files/" + account_id_to_dir(account_id)
    account_dir = get_account_dir(account_id)
    results = []
    if (not os.path.isdir(account_dir)):
        return results # early return. 
        
    for i in os.listdir(account_dir):
        if i.endswith(".xml"): 
            results.append(status_item(os.path.join(account_dir, i), i, files_dir_url))
        continue

    return results

########################################################################
########################################################################

def status_item(filepath, filename, files_dir_url):
    """summary information about the notification"""
    
    f = open(filepath)
    data = f.read()

    # Note, there are many options for parsing XML in Python
    # For this recipe, we're using Beautiful Soup, http://www.crummy.com/software/BeautifulSoup/
    xml = BeautifulSoup(data, "xml")
    envelope_id = xml.EnvelopeStatus.EnvelopeID.string

    # Get envelope's attributes. Since the recipients also have "Status" we CAN NOT just use
    # xml.EnvelopeStatus.Status.string since that returns the first Status *descendant* of EnvelopeStatus
    # (We want the first child). So we get the children this way:
    #
    # Set defaults for fields that may not be present
    sender_email = envelope_delivered_timestamp = envelope_created_timestamp = envelope_signed_timestamp =  None
    envelope_completed_timestamp = None
    # Now fill in the values that we can find:
    for child in xml.EnvelopeStatus:
        if child.name == "Status": envelope_status = child.string
        if child.name == "TimeGenerated": time_generated = child.string
        if child.name == "Subject": subject = child.string
        if child.name == "UserName": sender_user_name = child.string
        if child.name == "Email": sender_email = child.string
        if child.name == "Sent": envelope_sent_timestamp = child.string
        if child.name == "Created": envelope_created_timestamp = child.string
        if child.name == "Delivered": envelope_delivered_timestamp = child.string
        if child.name == "Signed": envelope_signed_timestamp = child.string
        if child.name == "Completed": envelope_completed_timestamp = child.string

    # iterate through the recipients
    recipients = []
    for recipient in xml.EnvelopeStatus.RecipientStatuses.children:
        if (recipient.string == "\n"):
            continue
        recipients.append({
            "type": recipient.Type.string,
            "email": recipient.Email.string,
            "user_name": recipient.UserName.string,
            "routing_order": recipient.RoutingOrder.string,
            "sent_timestamp": get_string(recipient.Sent),
            "delivered_timestamp": get_string(recipient.Delivered),
            "signed_timestamp": get_string(recipient.Signed),
            "status": recipient.Status.string
        })
        
    documents = []
    # iterate through the documents if the envelope is Completed
    if envelope_status == "Completed" and xml.DocumentPDFs:
        for pdf in xml.DocumentPDFs.children:
            if (pdf.string == "\n"):
                continue
            doc_filename = get_pdf_filename(pdf.DocumentType.string, pdf.Name.string)
            documents.append({
                "document_ID": get_string(pdf.DocumentID),
                "document_type": pdf.DocumentType.string,
                "name": pdf.Name.string,
                "url": files_dir_url + '/' + doc_filename
            })

    result = {
        "envelope_id": envelope_id,
        "xml_url": files_dir_url + '/' + filename,
        "time_generated": time_generated,
        "subject": subject,
        "sender_user_name": sender_user_name,
        "sender_email": sender_email,
        "envelope_status": envelope_status,
        "envelope_sent_timestamp": envelope_sent_timestamp,
        "envelope_created_timestamp": envelope_created_timestamp,
        "envelope_delivered_timestamp": envelope_delivered_timestamp,
        "envelope_signed_timestamp": envelope_signed_timestamp,
        "envelope_completed_timestamp": envelope_completed_timestamp,
        "recipients": recipients,
        "documents": documents}

    return result

def get_string(element):
    """Helper for safely pulling string from XML"""
    return None if element == None else element.string
    

########################################################################
########################################################################

def setup_output_dir(account_id):
    """ setup output dir for the account
    
    Store the file. Create directories as needed
    Some systems might still not like files or directories to start with numbers.
    So we prefix the account ids with A and the timestamps with T
    """     
    # Make the account's directory
    account_dir = get_account_dir(account_id)
    try:
        os.makedirs(account_dir)
    except OSError as e:
        if e.errno != 17: # FileExists error
            raise
        pass

def get_account_dir(account_id):
    # Some systems might still not like files or directories to start with numbers.
    # So we prefix the account ids with E
    
    # Make the account's directory
    files_dir = os.path.join(os.getcwd(), xml_file_dir)
    account_dir = os.path.join(files_dir, account_id_to_dir(account_id))
    return account_dir

def account_id_to_dir(account_id):
    return "A" + account_id
    
########################################################################
########################################################################

def webhook_listener():
    # Process the incoming webhook data. See the DocuSign Connect guide
    # for more information
    #
    # Strategy: examine the data to pull out the envelope_id and time_generated fields.
    # Then store the entire xml on our local file system using those fields.
    #
    # This function could also enter the data into a dbms, add it to a queue, etc.
    # Note that the total processing time of this function must be less than
    # 100 seconds to ensure that DocuSign's request to your app doesn't time out.
    # Tip: aim for no more than a couple of seconds! Use a separate queuing service
    # if need be.

    data = request.data # This is the entire incoming POST content.
                        # This is dependent on your web server. In this case, Flask
    cache = ds_cache.get() # Settings
      
    # Note, there are many options for parsing XML in Python
    # For this recipe, we're using Beautiful Soup, http://www.crummy.com/software/BeautifulSoup/

    xml = BeautifulSoup(data, "xml")
    envelope_id = xml.EnvelopeStatus.EnvelopeID.string
    time_generated = xml.EnvelopeStatus.TimeGenerated.string
    
    # "CustomFields appears in multiple places in the XML.
    # So we look for one with the right parent
    good_custom_fields = False
    for custom_fields in xml.EnvelopeStatus.find_all("CustomFields"):
        if custom_fields.parent.name == 'EnvelopeStatus':
            good_custom_fields = custom_fields

    if not good_custom_fields:
        ds_recipe_lib.log("Account number not found in XML, skipping!")
        return

    account_id = False
    for custom_field in good_custom_fields.children:
        # <Name>AccountId</Name>
        # <Value>1703272</Value>
        name = custom_field.find('Name')
        if name != -1 and name.string == "AccountId":
            account_id = custom_field.find('Value').string

    if not account_id:
        ds_recipe_lib.log("Account number not found in XML, skipping!")
        return
        
    # Check that the right template generated this notification
    template_name = xml.find("TemplateName") != None and xml.find("TemplateName").string
    if template_name != cache['template_name']:
        ds_recipe_lib.log("Missing or incorrect template name in XML, skipping!")
        return
    
    # Pull out the recipient 1 (PowerForm user) name and email
    # Check that the person actually signed!
    sender_name = None
    sender_email = None
    sender_signer = None
    for recipient in xml.RecipientStatuses.find_all("RecipientStatus"):
        r_type = recipient.find('Type')
        order = recipient.find('RoutingOrder')
        if (r_type != -1 and r_type.string == "Signer" 
            and order != -1 and order.string == '1'):
            sender_name = recipient.find('UserName').string
            sender_email = recipient.find('Email').string
            sender_signed = recipient.find('Status').string == "Completed"

    if sender_name:
        ds_recipe_lib.log("PowerForm sender (new partner): {} <{}>".format (
            sender_name, sender_email))
        if not sender_signed:
            ds_recipe_lib.log("The PowerForm sender didn't sign the contract!")
            return
    else:
        ds_recipe_lib.log("The PowerForm sender was not found in the XML, skipping!")
        return
        
    # Get the pname (Partner Name) field value
    # Get the pfname (Partner First Name) field value
    # Get the plname (Partner Last Name) field value
    # Get the wpartner (Partner url) field value
    partner_name = None
    partner_first_name = None
    partner_last_name = None
    sfdc_partner_url = None

    for tab in xml.find_all("TabStatus"):
        label = tab.find('TabLabel')
        value = tab.find('TabValue')
        if label != -1 and value != -1:
            if label.string == 'pname':
                partner_name = value.string
            if label.string == 'pfname':
                partner_first_name = value.string
            if label.string == 'plname':
                partner_last_name = value.string
            if label.string == 'wpartner':
                sfdc_partner_url = value.string
    
    if not partner_name or not sfdc_partner_url or not partner_first_name or not partner_last_name:
        ds_recipe_lib.log("The XML is missing the partner name and/or the SFDC URL, skipping!")
        return
    ds_recipe_lib.log("Partner name: {}, SFDC partner url: {}".format(partner_name, sfdc_partner_url))
    
    # Store the file.
    # Some systems might still not like files or directories to start with numbers.
    # So we prefix the envelope ids with E and the timestamps with T
    setup_output_dir(account_id)
    account_dir = get_account_dir(account_id)
    filename = "T" + time_generated.replace(':' , '_') + ".xml" # substitute _ for : for windows-land
    filepath = os.path.join(account_dir, filename)
    with open(filepath, "w") as xml_file:
        xml_file.write(data)
        
    ds_salesforce.provision_community_member(cache, sender_email, partner_first_name, partner_last_name, sfdc_partner_url)    
    
########################################################################
########################################################################

def get_pdf_filename(doc_type, pdf_name):
    if (doc_type == "CONTENT"):
        filename = 'Completed_' + pdf_name
    elif (doc_type == "SUMMARY"):
        filename = pdf_name
    else:
        filename = doc_type + "_" + pdf_name
    
    return filename

########################################################################
########################################################################

# FIN
