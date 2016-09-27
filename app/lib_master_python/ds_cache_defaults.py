# The default cache values
#
# Use this file to store information that needs to be available independent
# of a particular user's session.
# This is especially needed for credentials for "Service Integration" that just
# run in the background.

# Set encoding to utf8. See http:#stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')


# Global constants
defaults = {
    'ds_account_id': None, # can be looked up if not provided
    'ds_service_account_email': None,
    'ds_service_account_pw': None,
    'ds_service_client_id': None, # integration key
    'sfdc_username': None,
    'sfdc_pw': None,
    'sfdc_security_token': None,
    # For the following, see https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_objects_user.htm 
    'sfdc_user_type': 'Partner', # or Power Partner for partners
    'sfdc_profile_id': None, # Get the ID (from the URL) for the new members' profile. Eg "Partner Community Login User"
    'sfdc_time_zone_sid_key': 'America/Los_Angeles',
    'sfdc_locale_sid_key': 'en_US',
    'sfdc_email_encoding_key': 'ISO-8859-1', 
    'sfdc_language_locale_key': 'en_US',
    'sfdc_community_url': None,
    'sfdc_forgot_password': 'https://login.salesforce.com/secur/forgotpassword.jsp',
    'sfdc_user_name_domain': 'ex.com', # the "domain" that should be used to create user names for your community
                             # Should be related to your company/domain but not the same. 
                             # Eg ex.com instead of the real example.com
    
    # mailgun settings start with mg_ See www.mailgun.com
    'mg_domain': None, # eg mg.foo.com
    'mg_api_key': None,
    'template_name': "World Wide Co Partner Agreement" # name of your PowerForm's template
}

# Note
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
########################################################################

def get():
    """ Get the default values for the cache
    
        Returns: a dictionary of the cache
    """
    return defaults

########################################################################
########################################################################
########################################################################


## FIN ##

