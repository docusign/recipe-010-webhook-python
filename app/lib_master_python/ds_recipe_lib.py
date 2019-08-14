# Python Utilities for DocuSign Recipes

# Set encoding to utf8. See http:#stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import json, certifi, requests, os, base64, math, string, urllib, random, time, re
from flask import request
# See http:#requests.readthedocs.org/ for information on the requests library
# See https:#urllib3.readthedocs.org/en/latest/security.html for info on making secure https calls
# in particular, run pip install certifi periodically to pull in the latest cert bundle

# Set environment variables DS_USER_EMAIL, DS_USER_PW, and DS_INTEGRATION_ID
# Globals variables
ds_user_email = "" 
ds_user_pw = "" 
ds_integration_id = ""
ds_account_id = ""
ds_base_url = ""
ds_headers = ""
email_count = 2 # Used to make email addresses unique.

# Global constants
ds_api_login_url = "https://demo.docusign.net/restapi/v2/login_information" # change for production
ca_bundle = "app/static/assets_master/ca-bundle.crt"
temp_email_server = "mailinator.com" # Used for throw-away email addresses
b64_pw_prefix="ZW5jb"
b64_pw_clear_prefix="encoded"

def init (arg_ds_user_email, arg_ds_user_pw, arg_ds_integration_id, arg_ds_account_id = None):
    # if ds_account_id is null then the user's default account will be used
    # if ds_user_email is "***" then environment variables are used
    # Returns msg: None means no problem. Otherwise there is a problem
    
    global ds_user_email, ds_user_pw, ds_integration_id, ds_account_id, ds_base_url, ds_headers, email_count

    if (arg_ds_user_email == "***"):
        arg_ds_user_email = os.environ.get("DS_USER_EMAIL")
        arg_ds_user_pw = os.environ.get("DS_USER_PW")
        arg_ds_integration_id = os.environ.get("DS_INTEGRATION_ID")
        
    if (not isinstance(arg_ds_user_email, basestring) or len(arg_ds_user_email) < 7):
        return "No DocuSign login settings! " + \
        "Either set in the script or use environment variables DS_USER_EMAIL, DS_USER_PW, and DS_INTEGRATION_ID"
        # If the environment variables are set, but it isn't working, check that the
        # your http:#us.php.net/manual/en/ini.core.php#ini.variables-order ini setting includes "E" in the string.
        # See http:#php.net/manual/en/reserved.variables.environment.php


    # Decode the pw if it is in base64
    if (b64_pw_prefix == arg_ds_user_pw[:len(b64_pw_prefix)]):
        # it was encoded
        arg_ds_user_pw = base64.b64decode(arg_ds_user_pw)
        arg_ds_user_pw = arg_ds_user_pw[len(b64_pw_clear_prefix):] # remove prefix

    ds_user_email = arg_ds_user_email
    ds_user_pw = arg_ds_user_pw
    ds_integration_id = arg_ds_integration_id
    ds_account_id = arg_ds_account_id
    
    # construct the authentication header:
    ds_headers = {'Accept': 'application/json',
        'X-DocuSign-Authentication': "<DocuSignCredentials><Username>" + ds_user_email + 
        "</Username><Password>" + ds_user_pw + "</Password><IntegratorKey>" + 
        ds_integration_id + "</IntegratorKey></DocuSignCredentials>"}
        
    return None
    
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################

def login():
    # Login (to retrieve baseUrl and accountId)
    global ds_user_email, ds_user_pw, ds_integration_id, ds_account_id, ds_base_url, ds_headers, email_count
    try:
        r = requests.get(ds_api_login_url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        return ({'ok': False, 'msg': "Error calling DocuSign login: " + e})
        
    status = r.status_code
    if (status != 200): 
        return ({'ok': False, 'msg': "Error calling DocuSign login, status is: " + str(status)})

    # get the baseUrl and accountId from the response body
    response = r.json()
    # Example response:
    # { "loginAccounts": [ 
    #       { "name": "DocuSign", "accountId": "1374267", 
    #         "baseUrl": "https:#demo.docusign.net/restapi/v2/accounts/1374267", 
    #        "isDefault": "true", "userName": "Recipe Login", 
    #        "userId": "d43a4a6a-dbe7-491e-9bad-8f7b4cb7b1b5", 
    #        "email": "temp2+recipe@kluger.com", "siteDescription": ""
    #      } 
    # ]}
    #
    
    found = False
    errMsg = ""
    # Get account_id and base_url. 
    if (ds_account_id == None or ds_account_id == False):
        # Get default
        for account in response["loginAccounts"]:
            if (account["isDefault"] == "true"):
                ds_account_id = account["accountId"]
                ds_base_url = account["baseUrl"]
                found = True
                break
                
        if (not found):
            errMsg = "Could not find default account for the username."
    else:
        # get the account's base_url
        for account in response["loginAccounts"]:
            if (account["accountId"] == ds_account_id):
                ds_base_url = account["baseUrl"]
                found = True
                break
        if (not found):
            errMsg = "Could not find baseUrl for account " + ds_account_id
    
    return {'ok': found, 'msg': errMsg} 

########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################

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
    global ds_user_email, ds_user_pw, ds_integration_id, ds_account_id, ds_base_url, ds_headers, email_count
    ip = "100"
    email_count = math.pow(email_count, 2)
    email = str(email_count) + str(time.time())
    email = base64.b64encode (email)
    email = "a" + re.sub(r'[^A-Za-z0-9]', '', email) # strip non-alphanumeric characters
    return email + "@" + temp_email_server

def get_temp_email_access(email):
    # just create something unique to use with maildrop.cc
    # Read the email at https://www.mailinator.com/v3/index.jsp?zone=public&query=<mailbox_name>
    url = "https://mailinator.com/v3/index.jsp?zone=public&query="
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
########################################################################
########################################################################
########################################################################

def get_base_url():
    # Dynamically get the url one step before this script's url
    script_url = get_script_url()
    parts = script_url.split("/")
    del parts[-1]
    url = '/'.join(map(str, parts))
    return url

def get_script_url():
    # Dynamically determine the script's url
    # For production use, this is not a great idea. Instead, set it
    # explicitly. Remember that for production, webhook urls must start with
    # https!
    my_url = rm_queryparameters(full_url(request.environ))
        # See http://flask.pocoo.org/docs/0.10/api/#flask.request
    return my_url

# See http://stackoverflow.com/a/8891890/64904
def url_origin(s, use_forwarded_host = False):
    ssl      = (('HTTPS' in s) and s['HTTPS'] == 'on')
    sp       = s['SERVER_PROTOCOL'].lower()
    protocol = sp[:sp.find('/')] + ('s' if ssl else '' )
    port     = s['SERVER_PORT']
    port     = '' if ((not ssl and port=='80') or (ssl and port=='443')) else (':' + port)
    host     = s['HTTP_X_FORWARDED_HOST'] if (use_forwarded_host and ('HTTP_X_FORWARDED_HOST' in s)) \
                 else (s['HTTP_HOST'] if ('HTTP_HOST' in s) else None)
    host     = host if (host != None) else (s['SERVER_NAME'] + port)
    return protocol + '://' + host

def full_url(s, use_forwarded_host = False):
    return url_origin(s, use_forwarded_host) + (s['REQUEST_URI'] if ('REQUEST_URI' in s) else s['PATH_INFO'])

def rm_queryparameters (input):
    parts = string.split(input, "?")
    return parts[0]

########################################################################
########################################################################
########################################################################
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
    
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################    

## FIN ##

