# DocuSign Salesforce
#
# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')
import os, base64, json, requests, logging, random
from app.lib_master_python import ds_recipe_lib
from urlparse import urlparse
from simple_salesforce import Salesforce
from string import Template
import beatbox

# Constants
html_email_template = 'app/templates/welcome_email.html'   
    
########################################################################
########################################################################

# Notes
#
# See https://github.com/superfell/Beatbox for more info on beatbox
# (SFDC SOAP library) and procedures for when SFDC requies TLS 1.2
#
# For the user object, fields TimeZoneSidKey, LocaleSidKey, ProfileId,
# EmailEncodingKey, and LanguageLocaleKey are all required. But how
# to determine good default values? One was is to create a user,
# then see what those fields are set to for the existing user.
# Use the Python interpreter:
# from simple_salesforce import Salesforce
# from app.lib_master_python import ds_cache
# cache = ds_cache.get()
# sf = Salesforce(instance = 'samdev-dev-ed.my.salesforce.com', session_id='')
# sf = Salesforce(username = cache['sfdc_username'], password = cache['sfdc_pw'], security_token = cache['sfdc_security_token'])
# sf.User.get('00561000001veBp') # The existing User record ID
# Then use https://pythoniter.appspot.com/ to pretty print the resulting Python dict
    
########################################################################
########################################################################

def provision_community_member(cache, email, first_name, last_name, sfdc_account_url):
    '''Create a contact and external user in the sfdc account
    
    Returns err_msg => None or the problem info
    '''
    
    # Interpreter command to test this method
    # from app.lib_master_python import ds_salesforce; from app.lib_master_python import ds_cache; cache = ds_cache.get()
    # ds_salesforce.provision_community_member(cache, 'someone@mailinator.com', 'Sally', 'Ride', 'https://name-dev-ed.my.salesforce.com/0016100000cgXXX')
    
    ds_recipe_lib.log('################## Starting SFDC provisioning')
    
    # Check that the url is for an SFDC account
    # See http://www.salesforceben.com/salesforce-url-consist/
    url_parts = urlparse(sfdc_account_url)
    path = url_parts.path # includes leading /
    obj_prefix = path[1:4]
    account_obj_prefix = '001'
    account_id = path[1:]
    # ParseResult(scheme='http', netloc='www.cwi.nl:80', path='/%7Eguido/Python.html', params='', query='', fragment='')
    if obj_prefix != account_obj_prefix:
        return 'The SFDC url is not an Account reference'
    
    sf = Salesforce(instance = url_parts.netloc, session_id='')
    sf = Salesforce(username = cache['sfdc_username'], password = cache['sfdc_pw'], security_token = cache['sfdc_security_token'])
    
    # Create the contact
    r = sf.Contact.create ({'AccountID': account_id, 'LastName': last_name, 'FirstName': first_name, 'Email': email})
    if r['success']:
        ds_recipe_lib.log('Created contact for account {}!'.format(account_id))
        contact_id = r['id']
    else:
        ds_recipe_lib.log('ERROR creating contact for account {} -- {}'.format(account_id, str(r['errors'])))
        return 'Problem creating the contact: ' + str(r['errors'])
        
    # Create the user. See https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_objects_user.htm
    username = email.split('@')[0] + '@' + cache['sfdc_user_name_domain']
    ### In production, you'd want to automatically handle a username clash with an existing user,
    ### and then try alternate usernames for the new user.
    
    r = sf.User.create ({
                'ContactId': contact_id, 
                'Email': email, 
                'LastName': last_name, 
                'FirstName': first_name,
                'IsActive': True, 
                'ProfileId': cache['sfdc_profile_id'],
                'Username': username, 
                'UserPreferencesLightningExperiencePreferred': True,
                'Alias': first_name[0:0] + last_name[0:6], # Alias is required, max length 8. 
                    # In production you'd want to watch for alias clashes and then append a digit if needed
                'TimeZoneSidKey': cache['sfdc_time_zone_sid_key'],
                'LocaleSidKey': cache['sfdc_locale_sid_key'], 
                'EmailEncodingKey': cache['sfdc_email_encoding_key'], 
                'LanguageLocaleKey': cache['sfdc_language_locale_key'],
                'ProfileId': cache['sfdc_profile_id']
                })
    if r['success']:
        user_id = r['id']
        ds_recipe_lib.log('Created user record! ID = ' + user_id)
    else:
        ds_recipe_lib.log('ERROR creating user -- {}'.format(str(r['errors'])))
        return 'Problem creating the user: ' + str(r['errors'])
    
    send_welcome_email(cache, email, first_name, last_name, username)
    
    ds_recipe_lib.log('################## Completed SFDC provisioning')
    return None

def send_welcome_email(cache, email, first_name, last_name, username):
    '''Send the welcome email with instructions for setting password'''

    to = first_name + " " + last_name + " <" + email + ">"
    from_ = "New Partner Robot <mailgun@" + cache['mg_domain'] + ">"
    subject = "Your World Wide Partner Portal account was created"
    
    text_body = '''

Hello!

Thank you for joining the World Wide Corp Partner Program! 
This email includes your partner portal login instructions.

We look forward to working with you. Please let me know if
you have any questions or comments.

Best regards,

Juliette Morris, VP, Partnering
juliette.morris@worldwidecorp.us

~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ 

Login to your World Wide Partner Portal Account

===>>> Your portal user name is {username}  <<<===

Step 1. Set you password by filling in the "Reset Password" form: {reset_password_url}. Use your portal username {username2}

Step 2. Login to the portal: {portal_url}

'''.format(username = username, username2 = username, reset_password_url = cache['sfdc_forgot_password'], 
    portal_url = cache['sfdc_community_url'])
    
    # read in the html version of the email 
    html_body = Template(open(html_email_template, 'r').read()).substitute(
        username = username, reset_password_url = cache['sfdc_forgot_password'], 
        portal_url = cache['sfdc_community_url'])

    requests.post(
        'https://api.mailgun.net/v3/' + cache['mg_domain'] + '/messages',
        auth=("api", cache['mg_api_key']),
        data={"from": from_,
              "to": [to],
              "subject": subject,
              "text": text_body,
              "html": html_body})

# FIN
