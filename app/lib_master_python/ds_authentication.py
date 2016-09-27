# Python Authentication for DocuSign Recipes

# Set encoding to utf8. See http:#stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import json, certifi, requests, os, base64, math, string, urllib, random, time, datetime, re, hashlib, base64
from flask import request, session
from app.lib_master_python import ds_recipe_lib
from app.lib_master_python import ds_cache

# See http:#requests.readthedocs.org/ for information on the requests library
# See https:#urllib3.readthedocs.org/en/latest/security.html for info on making secure https calls
# in particular, run pip install certifi periodically to pull in the latest cert bundle

# Global constants
service_integration = True # True if this app needs its credentials independent of the user session mechanism
                           # If False, then this is a User App--each user's credentials are stored in her session
ds_account_id = None # If you're looking for a specific account_id, set this var
ds_legacy_login_url = "https://demo.docusign.net/restapi/v2/login_information" # change for production
oauth_authentication_server = "https://account-d.docusign.com/" # change for production
oauth_authentication_server = "https://account.docusign.com/" # production setting
oauth_start = oauth_authentication_server + "oauth/auth"
oauth_token = oauth_authentication_server + "oauth/token"
oauth_userInfo = oauth_authentication_server + "oauth/userinfo"
oauth_base_url_fragment = "/restapi/v2/" # Used to create base_url from base_uri
ca_bundle = "app/static/assets_master/ca-bundle.crt"
oauth_scope = "signature"

oauth_opportunistic_re_auth = 60 * 30 # refesh OAuth it expires in less than 30 minutes
oauth_force_token_refresh = False # Should we force token refresh?

# When an access token has expired, you'll get the error response:
# "errorCode": "AUTHORIZATION_INVALID_TOKEN"

########################################################################
########################################################################
########################################################################

# For User Apps, we're storing authentication in the Flask session which is
# stored in a server-side file. See app/lib_master_python/json_session_interface
#
# In production, the OAuth client_id (the integration_key) and related
# information would be constants for the application. Here we're enabling them to be set
# at runtime (stored in the session) so the recipes can be easily tried out.
#
# Info stored in the session:
# auth: {authenticated: true/false
#        user_name
#        email
#        type: {oauth_code, ds_legacy}
#        account_id
#        account_name
#        base_url           # Used for API calls
#        base_url_no_account # Used for account-independent API calls. Eg
#        auth_header_key    # Used for API calls
#        auth_header_value  # Used for API calls
#        client_id (integration_key)
#        client_secret
#        oauth_state # temp storage during authentication
#        refresh_token # OAuth code grant only
#        expires # timestamp when OAuth token expires
#
# auth_redirect: a url that should be redirected to after the authentication 
#                succeeds. Used when an operation needs re-authentication 
#                before it can be executed.

def get_service_integration_auth():
    """Returns auth information from the ds_cache"""
    global ds_account_id
    
    cache = ds_cache.get()
    auth = {}
    auth["err"] = False
    auth["err_code"] = False
    auth["cache"] = cache # May include extra stuff that is app-dependent (like SFDC creds)
    auth["email"] = cache['ds_service_account_email']
    auth["client_id"] = cache['ds_service_client_id']

    if ds_account_id == None:
        ds_account_id = cache['ds_account_id'] # Set the default
    
    auth_header_key = 'X-DocuSign-Authentication'
    auth_header_dict = {"Username": cache['ds_service_account_email'], "Password": cache['ds_service_account_pw'], 
        "IntegratorKey": cache['ds_service_client_id']}
    auth_header_value = json.dumps(auth_header_dict)
    r = authentication_login(auth_header_key, auth_header_value) # r is {err, account_id, base_url, base_url_no_account}

    if r["err"]:
        auth["err"] = r["err"]
        auth["err_code"] = 'LEGACY_USER_INFO'
        return auth

    auth["user_name"] = r["user_name"]
    auth["type"] = 'ds_legacy'
    auth["account_id"] = r["account_id"]    
    auth["account_name"] = r["account_name"]
    auth["base_url"] = r["base_url"]  # Used for API calls
    auth["base_url_no_account"] = r["base_url_no_account"]   # Used for account-independent API calls. Eg
    auth["auth_header_key"] = auth_header_key  # Used for API calls
    auth["auth_header_value"] = auth_header_value  # Used for API calls
    
    session["auth"] = auth
    
    return auth

def get_service_integration_auth_status():
    """Returns the authentication status

    Returns a dictionary:
    auth_status = {
        authenticated: true/false,
        oauth_redirect: false, or the url that the browser should be redirected to accomplish re-authentication
        description: string. Eg "Authenticated as John Doe <john@doe.com> for account 12345"
            or "Not authenticated"
        auth: the auth object
        }
    """
    translator = {"oauth_code": "OAuth Authorization Code Grant",
                  "ds_legacy": "DocuSign Legacy Authentication"}
        
    auth = get_service_integration_auth()
    auth_status = {}
    auth_status["oauth_redirect"] = False
    auth_status["auth"] = auth
    if auth["err"]:
        auth_status["authenticated"] = False
        auth_status["description"] = "Not authenticated: " + auth["err"]
    else:
        auth_status["authenticated"] = True
        auth_status['description'] = 'Authenticated via {} as {} &lt;{}&gt; for the {} account ({}).'.format(
            translator[auth['type']], auth['user_name'], auth['email'], auth['account_name'], auth['account_id'])
    return auth_status

def reauthenticate_check(r, redirect):
    """If need be, provide redirect for reauthentication
    
    Parameters: r -- a general method response. Field err_code will be examined
                     If it is PLEASE_REAUTHENTICATE then the session will be setup 
                     to redirect after auth and the auth redirect url will be returned
                redirect -- where the browser should be redirected after a successful
                            re-suthentication.
    
    Returns: False or the redirect url
    """
    if service_integration:
        # No need for re-authentication for Service apps
        return False 
    
    # See if we're testing the re-authentication
    oauth_force_re_auth = False
    if "oauth_force_re_auth" in session:
        oauth_force_re_auth = session["oauth_force_re_auth"]
        if oauth_force_re_auth:
            # Check that we can do a re-authentication
            auth = session["auth"]
            oauth_force_re_auth = (auth["type"] == "oauth_code" and auth["client_id"] and auth["secret_key"]
                and auth["redirect_uri"])
            session["oauth_force_re_auth"] = False # reset
            
    if oauth_force_re_auth:
        ds_recipe_lib.log("reauthenticate_check: forcing re-authentication...")
    
    if oauth_force_re_auth or ('err_code' in r and r['err_code'] == "PLEASE_REAUTHENTICATE"):
        session["auth_redirect"] = redirect
        ds_recipe_lib.log("reauthenticate_check: final redirect will be to " + redirect)
        
        auth = session["auth"]
        oauth_state = hashlib.sha256(os.urandom(1024)).hexdigest()
        auth["oauth_state"] = oauth_state 
        session["auth"] = auth # Store updated info
        
        redirect = (oauth_start +
            "?response_type=code" +
            "&scope=" + oauth_scope +
            "&client_id=" + auth["client_id"] +
            "&state=" + oauth_state +
            "&redirect_uri=" + auth["redirect_uri"])
            
        return redirect
    else:
        return False

def get_auth():
    """Gets auth info from session and checks it
    
    If OAuth is used, and the token is about to expire, this method will refresh it.
    If the token couldn't be refreshed, then an err_code of "PLEASE_AUTHENTICATE" or "PLEASE_REAUTHENTICATE" is returned.
    Returns: the contents of session["auth"] with some new fields:
       err -- false means no problems. Or it contains a string with the problem info
       err_code -- false, PLEASE_AUTHENTICATE or PLEASE_REAUTHENTICATE
    """
    
    if service_integration:
        return get_service_integration_auth()
    
    if 'auth' in session:
        auth = session['auth']
        if not auth["authenticated"]:
            auth["err"] = "Please authenticate with DocuSign."
            auth["err_code"] = "PLEASE_AUTHENTICATE"
            return auth
    else:
        auth = {}
        auth["err"] = "Please authenticate with DocuSign."
        auth["err_code"] = "PLEASE_AUTHENTICATE"
        return auth
    
    if auth["type"] == "oauth_code" and (((auth["expires"] - int(time.time())) < oauth_opportunistic_re_auth) 
        or oauth_force_token_refresh):
        re_authenticate = token_refresh(auth)
        if re_authenticate:
            if auth["client_id"] and auth["secret_key"]:
                auth["err"] = "Please re-authenticate with DocuSign."
                auth["err_code"] = "PLEASE_REAUTHENTICATE"
            else:
                auth["err"] = "Please authenticate with DocuSign."
                auth["err_code"] = "PLEASE_AUTHENTICATE"                
            return auth
    
    auth["err"] = False
    auth["err_code"] = False
    return auth

def token_refresh(auth):
    """Call OAuth: token_refresh
    
    Returns true if the user needs to re-authenticate.
        False indicates that the refresh worked and there is still time 
              left on the new token
    """
    
    client_secret = auth["client_id"] + ':' + auth["secret_key"]
    client_secret_b64 = base64.b64encode(client_secret)
    
    try:
        r = requests.post(oauth_token,
                headers={'Authorization': "Basic " + client_secret_b64},
                data={'grant_type': 'refresh_token', 'refresh_token': auth["refresh_token"]})
    except requests.exceptions.RequestException as e:
        err = "Error calling DocuSign for OAuth token refresh: " + str(e)
        ds_recipe_lib.log(err)
        return True

    status = r.status_code
    if (status != 200):
        err =  "Error calling DocuSign for OAuth token refresh: " + r.content + " (" + str(status) + "). "
        ds_recipe_lib.log(err)
        return True
            
    # we should now have the following in r.json() --
    # access_token	The token you will use in the Authorization header of calls to the DocuSign API.
    # token_type	This is the kind of token. It is usually Bearer
    # refresh_token	A token you can use to get a new access_token without requiring user interaction.
    # expires_in	The number of seconds before the access_token expires.
    #
    # Example content: {"access_token":"[587 characters]","token_type":"Bearer","refresh_token":"[587 characters]","expires_in":28800,"user_api":null}
    token_info = r.json()

    # Save in the session.
    auth['access_token'] = token_info["access_token"]
    auth['refresh_token'] = token_info["refresh_token"]
    auth['token_type'] = token_info["token_type"]
    auth["auth_header_key"] = "Authorization"
    auth["auth_header_value"] = auth['token_type'] + " " + auth['access_token']
    auth["expires"] = int(time.time()) + token_info["expires_in"]
    
    expires_soon = (auth["expires"] - int(time.time())) < oauth_opportunistic_re_auth
    if expires_soon:
        ds_recipe_lib.log("Token refresh: we have a good response, but the new token also expires soon!")
        return True

    ds_recipe_lib.log("Token refresh: Success! Expires in " + str(datetime.timedelta(seconds= auth["expires"] - int(time.time()))))    
    
    # Save info
    session["auth"] = auth
    return False

def get_auth_status(redirecting=False):
    """Returns the authentication status of the current session

    Parameter redirecting: is the user in the process of being redirected to OAuth?
    Returns a dictionary:
    auth_status = {
        authenticated: true/false,
        oauth_redirect: false, or the url that the browser should be redirected to accomplish re-authentication
        description: string. Eg "Authenticated as John Doe <john@doe.com> for account 12345"
            or "Not authenticated"
        auth: the auth object
        }
    """
    
    if service_integration:
        return get_service_integration_auth_status()
    
    auth_status = {}
    translator = {"oauth_code": "OAuth Authorization Code Grant",
                  "ds_legacy": "DocuSign Legacy Authentication"}

    if 'auth' in session:
        auth = session['auth']
    else:
        auth = {'authenticated': False}

    auth_status['authenticated'] = auth['authenticated']
    auth_status["oauth_redirect"] = False
    auth_status['auth'] = auth
    if auth['authenticated']:
        auth_status['description'] = 'Authenticated via {} as {} &lt;{}&gt; for the {} account ({}).'.format(
            translator[auth['type']], auth['user_name'], auth['email'], auth['account_name'], auth['account_id'])
        if auth['type'] == 'oauth_code':
            time_left = auth["expires"] - int(time.time())
            if time_left > 0:
                auth_status['token_expiration'] = ("The OAuth token expires in " + 
                    str(datetime.timedelta(seconds= time_left)))
            else:  # Already expired
                auth_status['token_expiration'] = ("The OAuth token has expired. A Token Refresh will be attempted.")                
            auth_status['description'] += " </br>" + auth_status['token_expiration']
    else:
        # Two options:
        if (not redirecting and "type" in auth and auth["type"] == "oauth_code" and 
            "client_id" in auth and auth["client_id"] and
            "secret_key" in auth and auth["secret_key"]):
            # re-authenticate via OAuth
            oauth_state = hashlib.sha256(os.urandom(1024)).hexdigest()
            auth["oauth_state"] = oauth_state 
            session["auth"] = auth # Store updated info            
            
            auth_status["oauth_redirect"] = (oauth_start +
                "?response_type=code" +
                "&scope=" + oauth_scope +
                "&client_id=" + auth["client_id"] +
                "&state=" + oauth_state +
                "&redirect_uri=" + auth["redirect_uri"])
        else:
            auth_status['description'] = "You are not authenticated. Please submit your authentication information:"

    return auth_status

def set_auth():
    """Enables the authentication to be set for the session.

    The Request body:
    type: {oauth_code, ds_legacy}

    code_client_id
    code_secret_key
    code_redirect_uri

    legacy_client_id: # same as integration_key. Required.
    legacy_email, # only supply if type == ds_legacy
    legacy_pw # only supply if type == ds_legacy

    The Response:
    {redirect: string, # If not False, then redirect the user's browser to this address to
                       # continue the auth process
     auth_status: same as from get_auth_status
     err: if not false then it contains the error message
    """

    req = request.get_json()
    delete_auth()
    if req["type"] == "ds_legacy":
        err = set_auth_ds_legacy(req)
        return {"err": err, "redirect": False, "auth_status": get_auth_status()}

    if req["type"] == "oauth_code":
        r = set_auth_oauth_code(req)
        return {"err": r["err"], "redirect": r["redirect"], "auth_status": get_auth_status(True)}

def set_auth_ds_legacy(req):
    """Authenticate the user using legacy technique

    Side-effect: Sets Session["auth"]
    Returns err
    """

    # Normally, the client_id (Integration_key) is a constant for the app.
    auth_header_key = 'X-DocuSign-Authentication'
    auth_header_dict = {"Username": req["legacy_email"], "Password": req["legacy_pw"], "IntegratorKey": req["legacy_client_id"]}
    auth_header_value = json.dumps(auth_header_dict)
    r = authentication_login(auth_header_key, auth_header_value) # r is {err, account_id, base_url, base_url_no_account}

    if r["err"]:
        return r["err"]

    # Set Session["auth"]
    session["auth"] = {"authenticated": True,
        "user_name": r["user_name"],
        "email": r["email"],
        "type": req["type"],
        "account_id": r["account_id"],
        "account_name": r["account_name"],
        "base_url": r["base_url"],
        "base_url_no_account": r["base_url_no_account"],
        "auth_header_key": auth_header_key,
        "auth_header_value": auth_header_value}
    return False

def set_auth_oauth_code(req):
    """Start OAuth Authorization Code Grant process

    Store the Client ID and Secret in the session for later use when exchanging the code for a token

    Returns {err, redirect} where err is False or an error message
    """

    # Normally, the client_id (Integration_key), secret_key, and redirect_uri values are constants for the app.
    client_id = req["code_client_id"]
    secret_key = req["code_secret_key"]
    redirect_uri = req["code_redirect_uri"]

    if not client_id:
        return {"err": "Please include the Client ID (Integration Key)", "redirect": False}
    if not secret_key:
        return {"err": "Please include the Secret Key", "redirect": False}
    if not redirect_uri:
        return {"err": "Please include the Redirect URI", "redirect": False}

    # See https://developers.google.com/identity/protocols/OpenIDConnect#createxsrftoken
    oauth_state = hashlib.sha256(os.urandom(1024)).hexdigest()

    # Save info for later use
    session["auth"] = {"authenticated": False,
                       "type": req["type"],
                       "client_id": client_id,
                       "secret_key": secret_key,
                       "oauth_state": oauth_state,
                       "redirect_uri": redirect_uri}    
    
    redirect = (oauth_start +
        "?response_type=code" +
        "&scope=" + oauth_scope +
        "&client_id=" + client_id +
        "&state=" + oauth_state +
        "&redirect_uri=" + redirect_uri)

    return {"err": False, "redirect": redirect}

def authentication_login(auth_header_key, auth_header_value):
    """Call the Authentication: login method, which is only used for legacy authentication

    Returns {err, account_id, base_url, base_url_no_account, user_name, email}
    """
    ds_headers = {'Accept': 'application/json'}
    ds_headers[auth_header_key] = auth_header_value
    err = False

    try:
        r = requests.get(ds_legacy_login_url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        err = "Error calling DocuSign login: " + str(e)
        return {'err': err}

    status = r.status_code
    if (status != 200):
        return ({'err': "Error calling DocuSign login, status is: " + r.content + " (" + str(status) + ")"})

    # get the baseUrl and accountId from the response body
    response = r.json()
    # Example response:
    # { "loginAccounts": [
    #       { "name": "DocuSign",   # account_name
    #         "accountId": "1374267",
    #         "baseUrl": "https://demo.docusign.net/restapi/v2/accounts/1374267",
    #         "isDefault": "true",
    #         "userName": "Recipe Login",
    #         "userId": "d43a4a6a-dbe7-491e-9bad-8f7b4cb7b1b5",
    #         "email": "temp2+recipe@kluger.com",
    #         "siteDescription": ""
    #      }
    # ]}
    #

    account_id = None
    found = False
    user_name = None
    email = None
    # Get account_id and base_url.
    if (ds_account_id == None):
        # Get default
        for account in response["loginAccounts"]:
            if (account["isDefault"] == "true"):
                account_id = account["accountId"]
                account_name =account["name"]
                base_url = account["baseUrl"]
                base_url_no_account = rm_url_parts(base_url, 2)
                user_name = account["userName"]
                email = account["email"]
                found = True
                break

        if (not found):
            err = "Could not find default account for the username."
    else:
        # get the account's base_url
        for account in response["loginAccounts"]:
            if (account["accountId"] == ds_account_id):
                base_url = account["baseUrl"]
                base_url_no_account = rm_url_parts(base_url, 2)
                user_name = account["userName"]
                email = account["email"]
                account_id = ds_account_id
                account_name =account["name"]
                found = True
                break
        if (not found):
            err = "Could not find baseUrl for account " + ds_account_id

    return {'err': err, 'account_id': account_id, 'base_url': base_url, 'base_url_no_account': base_url_no_account,
            "user_name": user_name, "email": email, "account_name": account_name}


########################################################################
########################################################################

def rm_url_parts (url, remove):
    """Dynamically get the url <remove> steps before the original url"""

    parts = url.split("/")
    for x in range(0, remove):
        del parts[-1]
    url = '/'.join(map(str, parts))
    return url

########################################################################
########################################################################

def delete_auth():
    """Delete the session's authentication information"""
    session["auth"] = {"authenticated": False}
    return {"err": False}

########################################################################
########################################################################

def auth_redirect():
    """Process the incoming data from OAuth Authorization Code Grant redirect"""

    # An unsuccessful authentication redirect (User chose to not grant access)
    # error=access_denied&error_message=The%20user%20did%20not%20consent%20to%20connecting%20the%20application.&state=c611e8268536e1218f24f6991f1abd1a3c23cbbe6787887afc3138aede2f1840
    # Success:
    # code=eyJ0eXAiOi_blah_blah_P6BwFtw&state=70a5333877c3f57bcdc407a7776c747290f95ce8ec1ff5203d6af35e9d5b36e3

    # First check that the state is correct. This is important to prevent CSRF attacks. See http://goo.gl/av06hU
    # In this example, the user is notified of the behavior.
    # You might also want to alert an administrator or two. Or log all of the request's information

    ds_recipe_lib.log("Received incoming data from OAuth Authorization Code Grant redirect")
    if 'auth' in session and 'oauth_state' in session['auth']:
        auth = session['auth']
    else:
        e = "No authentication information in the session! Possible CSRF attack!"
        ds_recipe_lib.log("OAuth problem: " + e)       
        delete_auth()
        return e

    oauth_state = auth['oauth_state']
    incoming_state = request.args.get('state')
    if incoming_state != oauth_state:
        e = "Authentication state information mismatch! Possible CSRF attack!"
        ds_recipe_lib.log("OAuth problem: " + e)        
        ds_recipe_lib.log("Incoming state: " + incoming_state + " Stored state: " + oauth_state)        
        delete_auth()
        return e
        
    incoming_error_message = request.args.get('error_message')
    if incoming_error_message:
        ds_recipe_lib.log("OAuth error message: " + incoming_error_message)        
        delete_auth()
        return incoming_error_message

    incoming_code = request.args.get('code')
    if not incoming_code:
        e = "Code was not supplied by server! Please contact your administrator."
        ds_recipe_lib.log("OAuth problem: " + e)        
        delete_auth()
        return e

    # Exchange the code for tokens
    e = oauth_token_for_code(auth, incoming_code)
    if e:
        ds_recipe_lib.log("OAuth problem converting code to token: " + e)
        delete_auth()
        return e
    else:
        ds_recipe_lib.log("OAuth: converted code to token!")        

    # Get the User Info
    e = get_oauth_user_info()
    if e:
        ds_recipe_lib.log("OAuth problem getting user info: " + e)        
    else:
        ds_recipe_lib.log("OAuth: got user info!")        
    return e  # If no errors, then continue. The user is now authenticated!

def oauth_token_for_code(auth, code):
    """Calls the authentication service to get the tokens in return for the code

    Returns err (an error message) or False to indicate no problems
    """
    client_secret = auth["client_id"] + ':' + auth["secret_key"]
    client_secret_b64 = base64.b64encode(client_secret)

    try:
        r = requests.post(oauth_token,
                headers={'Authorization': "Basic " + client_secret_b64},
                data={'grant_type': 'authorization_code', 'code': code})
    except requests.exceptions.RequestException as e:
        err = "Error calling DocuSign for OAuth token: " + str(e)
        return err

    status = r.status_code
    if (status != 200):
        extra = "Tip: check that your secret key is correct."
        return "Error calling DocuSign for OAuth token: " + r.content + " (" + str(status) + "). " + extra

    # we should now have the following in r.json() --
    # access_token	The token you will use in the Authorization header of calls to the DocuSign API.
    # token_type	This is the kind of token. It is usually Bearer
    # refresh_token	A token you can use to get a new access_token without requiring user interaction.
    # expires_in	The number of seconds before the access_token expires.
    #
    # Example content: {"access_token":"[587 characters]","token_type":"Bearer","refresh_token":"[587 characters]","expires_in":28800,"user_api":null}

    token_info = r.json()

    # Save in the session.
    auth['access_token'] = token_info["access_token"]
    auth['refresh_token'] = token_info["refresh_token"]
    auth['token_type'] = token_info["token_type"]
    auth["auth_header_key"] = "Authorization"
    auth["auth_header_value"] = auth['token_type'] + " " + auth['access_token']
    auth["expires"] = int(time.time()) + token_info["expires_in"]

    # Save info
    session["auth"] = auth
    return False

def get_oauth_user_info():
    """Call the OAuth: userInfo method, which is only used for OAuth authentication

    Returns err
    Side-effect: Sets session["auth"]
    """

    auth = session["auth"]
    ds_headers = {'Accept': 'application/json'}
    ds_headers[auth["auth_header_key"]] = auth["auth_header_value"]
    err = False

    try:
        r = requests.get(oauth_userInfo, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        err = "Error calling DocuSign login: " + str(e)
        return err

    status = r.status_code
    if (status != 200):
        return "Error calling DocuSign OAuth userInfo: " + r.content + " (" + str(status) + ")"

    # get info from the response body
    response = r.json()
    # Example response:
    # {
    #     "sub": "50d89ab1-dad5-4a0a-1234-1234567890",
    #     "accounts": [
    #         {
    #          "account_id": "e783eff5-53e1-45b2-1234-1234567890",
    #          "is_default": true,
    #          "account_name": "NewCo",
    #          "base_uri": "https://demo.docusign.net"
    #          }
    #     ],
    #     "name": "Susan Smith",
    #     "given_name": "Susan",
    #     "family_name": "Smith",
    #     "email": "susan.smith@example.com"
    # }

    account_id = None
    found = False
    user_name = response["name"]
    email = response["email"]
    # Get account_id and base_url.
    if ds_account_id == None:
        # Get default
        for account in response["accounts"]:
            if account["is_default"]:
                account_id = account["account_id"]
                account_name = account["account_name"]
                base_uri = account["base_uri"]
                found = True
                break

        if not found:
            return "Could not find default account for " + user_name
    else:
        # get the account's base_url
        for account in response["accounts"]:
            if (account["account_id"] == ds_account_id):
                base_uri = account["base_uri"]
                account_id = ds_account_id
                account_name = account["account_name"]
                found = True
                break
        if not found:
            return "Could not find baseUrl for account " + ds_account_id

    # Add to Auth and store
    auth["authenticated"] = True
    auth["user_name"] = user_name
    auth["email"] = email
    auth["account_id"] = account_id
    auth["account_name"] = account_name
    auth["base_url"] = base_uri + oauth_base_url_fragment + "accounts/" + account_id
    auth["base_url_no_account"] = base_uri + oauth_base_url_fragment

    session["auth"] = auth

########################################################################
########################################################################
########################################################################


## FIN ##

