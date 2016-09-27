# Python Utilities for DocuSign Recipes

# Set encoding to utf8. See http:#stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import os, base64, string, urllib, random, re, json
from flask import request
# See http:#requests.readthedocs.org/ for information on the requests library
# See https:#urllib3.readthedocs.org/en/latest/security.html for info on making secure https calls
# in particular, run pip install certifi periodically to pull in the latest cert bundle

# Global constants
ds_api_login_url = "https://demo.docusign.net/restapi/v2/login_information" # change for production
ca_bundle = "app/static/assets_master/ca-bundle.crt"
temp_email_server = "mailinator.com" # Used for throw-away email addresses
heroku_env = 'DYNO' # Used to detect if we're on Heroku

########################################################################
########################################################################
########################################################################

def log(msg):
    sys.stderr.write("### ### ### " + str(msg) + "\n")

def log_obj(msg, obj):
    obj_str = json.dumps(obj, sort_keys=True, indent=4, separators=(',', ': '))
    sys.stderr.write("### ### ### " + str(msg) + ": " + obj_str + "\n")


def get_signer_name(name):
    if (not name or name == "***"):
        name = get_fake_name()
    return name

def get_signer_email(email):
    if (email and email != "***"):
        return email
    else:
        return make_temp_email()

def make_temp_email():
    # just create something unique to use with maildrop.cc
    # Read the email at http:#maildrop.cc/inbox/<mailbox_name>  
    ip = "100"
    email = base64.b64encode (os.urandom(15))
    email = "a" + re.sub(r'[^A-Za-z0-9]', '', email) # strip non-alphanumeric characters
    return email + "@" + temp_email_server

def get_temp_email_access(email):
    # just create something unique to use with maildrop.cc
    # Read the email at https://mailinator.com/inbox2.jsp?public_to=<mailbox_name>
    url = "https://mailinator.com/inbox2.jsp?public_to="
    parts = string.split(email, "@")
    if (parts[1] != temp_email_server):
        return False
    return url + parts[0]

def get_temp_email_access_qrcode(address):
    # url = "http://open.visualead.com/?size=130&type=png&data="
    url = "https://chart.googleapis.com/chart?cht=qr&chs=150x150&"
    url += urllib.urlencode ({"chl": address})
    size = 150
    html = "<img height='size' width='size' src='" + url + "' alt='QR Code' style='margin:10px 0 10px' />"
    return html

########################################################################
########################################################################
########################################################################

def get_base_url(remove=1):
    # Dynamically get the url <remove> steps before this script's url
    script_url = get_script_url()
    parts = script_url.split("/")
    for x in range(0, remove):
        del parts[-1]
    url = '/'.join(map(str, parts))
    if url.endswith('/'):
        url = url[:-1]
    return url

def get_script_url():
    # Dynamically determine the script's url
    # For production use, this is not a great idea. Instead, set it
    # explicitly. Remember that for production, webhook urls must start with
    # https!
    my_url = rm_queryparameters(full_url(request.environ))
        # See http://flask.pocoo.org/docs/0.10/api/#flask.request
    return my_url

def full_url(s):
    return url_origin(s) + (s['REQUEST_URI'] if ('REQUEST_URI' in s) else s['PATH_INFO'])

# See http://stackoverflow.com/a/8891890/64904
def url_origin(s, use_forwarded_host = False):
    
    # testing if Heroku includes forwarding host 
    use_forwarded_host = True
    include_protocol = True
    
    ssl      = (('HTTPS' in s) and s['HTTPS'] == 'on')
    sp       = s['SERVER_PROTOCOL'].lower()
    protocol = sp[:sp.find('/')] + ('s' if ssl else '' )
    port     = s['SERVER_PORT']
    port     = '' if ((not ssl and port=='80') or (ssl and port=='443')) else (':' + port)
    host     = s['HTTP_X_FORWARDED_HOST'] if (use_forwarded_host and ('HTTP_X_FORWARDED_HOST' in s)) \
                 else (s['HTTP_HOST'] if ('HTTP_HOST' in s) else None)
    host     = host if (host != None) else (s['SERVER_NAME'] + port)
    
    # The protocol can easily be wrong if we're frontended by a HTTPS proxy
    # (Like the standard Heroku setup!)
    on_heroku = heroku_env in os.environ
    upgrade_insecure_request = request.headers.get('Upgrade-Insecure-Requests')
    upgrade_insecure_request = upgrade_insecure_request and upgrade_insecure_request == 1
    https_proto = request.headers.get('X-Forwarded-Proto')
    https_proto = https_proto and https_proto == 'https'
    use_https = on_heroku or upgrade_insecure_request or https_proto
    if use_https: # Special handling
        protocol = "https"
    return protocol + '://' + host
        
def rm_queryparameters (input):
    parts = string.split(input, "?")
    return parts[0]

########################################################################
########################################################################
########################################################################    
    
def get_fake_name():
    first_names = ["Verna", "Walter", "Blanche", "Gilbert", "Cody", "Kathy",
    "Judith", "Victoria", "Jason", "Meghan", "Flora", "Joseph", "Rafael",
    "Tamara", "Eddie", "Logan", "Otto", "Jamie", "Mark", "Brian", "Dolores",
    "Fred", "Oscar", "Jeremy", "Margart", "Jennie", "Raymond", "Pamela",
    "David", "Colleen", "Marjorie", "Darlene", "Ronald", "Glenda", "Morris",
    "Myrtis", "Amanda", "Gregory", "Ariana", "Lucinda", "Stella", "James",
    "Nathaniel", "Maria", "Cynthia", "Amy", "Sylvia", "Dorothy", "Kenneth",
    "Jackie"]
    last_names = ["Francisco", "Deal", "Hyde", "Benson", "Williamson", 
    "Bingham", "Alderman", "Wyman", "McElroy", "Vanmeter", "Wright", "Whitaker", 
    "Kerr", "Shaver", "Carmona", "Gremillion", "O'Neill", "Markert", "Bell", 
    "King", "Cooper", "Allard", "Vigil", "Thomas", "Luna", "Williams", 
    "Fleming", "Byrd", "Chaisson", "McLeod", "Singleton", "Alexander", 
    "Harrington", "McClain", "Keels", "Jackson", "Milne", "Diaz", "Mayfield", 
    "Burnham", "Gardner", "Crawford", "Delgado", "Pape", "Bunyard", "Swain", 
    "Conaway", "Hetrick", "Lynn", "Petersen"]

    random.seed()
    first = first_names[random.randint(0, len(first_names) - 1)]
    last = last_names[random.randint(0, len(last_names) - 1)]
    return first + " " + last

## FIN ##

