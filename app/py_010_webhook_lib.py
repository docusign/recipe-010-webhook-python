# DocuSign API Walkthrough 04 (PYTHON) - Add Signature Request to Document and Send
#
# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import json, socket, certifi, requests, os, base64, re, urllib, shutil
# See http://requests.readthedocs.org/ for information on the requests library
# See https://urllib3.readthedocs.org/en/latest/security.html for info on making secure https calls
# in particular, run pip install certifi periodically to pull in the latest cert bundle

from lib_master_python import ds_recipe_lib
from flask import request
from bs4 import BeautifulSoup

# Enter your info here
# Or set environment variables DS_USER_EMAIL, DS_USER_PW, and DS_INTEGRATION_ID
# Globals:
ds_user_email = "***"
ds_user_pw = "***"
ds_integration_id = "***"
ds_account_id = False
doc_document_path = "app/static/sample_documents_master/NDA.pdf"
doc_document_name = "NDA.pdf"
webhook_path = "/webhook"
ds_signer1_email = "***"
ds_signer1_name = "***"
ds_cc1_email = "***"
ds_cc1_name = "***"
xml_file_dir = "app/files/"
readme = "ReadMe.txt"

def send():
    global ds_account_id, ds_signer1_email, ds_signer1_name, ds_cc1_email, ds_cc1_name
    msg = ds_recipe_lib.init(ds_user_email, ds_user_pw, ds_integration_id, ds_account_id)
    if (msg != None):
        return {'ok': False, 'msg': msg}

    # Ready...
    # Possible create some fake people
    ds_signer1_email = ds_recipe_lib.get_signer_email(ds_signer1_email)
    ds_signer1_name = ds_recipe_lib.get_signer_name(ds_signer1_name)
    ds_cc1_email = ds_recipe_lib.get_signer_email(ds_cc1_email)
    ds_cc1_name = ds_recipe_lib.get_signer_name(ds_cc1_name)

    # STEP 1 - Login
    r = ds_recipe_lib.login()
    if (not r["ok"]):
        return r
    ds_account_id = ds_recipe_lib.ds_account_id    

    #
    # STEP 2 - Create and send envelope with eventNotification
    #
    webhook_url = ds_recipe_lib.get_base_url() + webhook_path
    webhook_url = webhook_url.replace("http","https")
    event_notification = {"url": webhook_url,
        "loggingEnabled": "true", # The api wants strings for true/false
        "requireAcknowledgment": "true",
        "useSoapInterface": "false",
        "includeCertificateWithSoap": "false",
        "signMessageWithX509Cert": "false",
        "includeDocuments": "true",
        "includeEnvelopeVoidReason": "true",
        "includeTimeZone": "true",
        "includeSenderAccountAsCustomField": "true",
        "includeDocumentFields": "true",
        "includeCertificateOfCompletion": "true",
        "envelopeEvents": [ # for this recipe, we're requesting notifications
                            # for all envelope and recipient events
            {"envelopeEventStatusCode": "sent"},
            {"envelopeEventStatusCode": "delivered"},
            {"envelopeEventStatusCode": "completed"},
            {"envelopeEventStatusCode": "declined"},
            {"envelopeEventStatusCode": "voided"}],
        "recipientEvents": [
            {"recipientEventStatusCode": "Sent"},
            {"recipientEventStatusCode": "Delivered"},
            {"recipientEventStatusCode": "Completed"},
            {"recipientEventStatusCode": "Declined"},
            {"recipientEventStatusCode": "AuthenticationFailed"},
            {"recipientEventStatusCode": "AutoResponded"}]
    }

    # construct the body of the request
    file_contents = open(doc_document_path, "rb").read()

    # Our goal: provide an email subject that is most meaningful to the recipients
    # The regex strips the 3 or 4 character extension from the filename.
    subject = "Please sign the " + re.sub('/\\.[^.\\s]{3,4}$/', '', doc_document_name) + " document"
    # File contents provided here instead of a multi-part request
    docs = [{"documentId": "1", 
            "name": doc_document_name,
            "documentBase64": base64.b64encode(file_contents)}]
    
    signers = [{"email": ds_signer1_email,
                "name": ds_signer1_name,
                "recipientId": "1",
                "routingOrder": "1",
                "tabs": nda_fields()}]
    
    ccs = [{"email": ds_cc1_email,
            "name": ds_cc1_name,
            "recipientId": "2",
            "routingOrder": "2"}]
    
    data = {"emailSubject": subject,
            "documents": docs, 
            "recipients": {"signers": signers, "carbonCopies": ccs},
            "eventNotification": event_notification,
            "status": "sent"
    }
        
    # append "/envelopes" to the baseUrl and use in the request
    url = ds_recipe_lib.ds_base_url + "/envelopes"
    try:
        r = requests.post(url, headers=ds_recipe_lib.ds_headers, json=data)
    except requests.exceptions.RequestException as e:
        return {'ok': False, 'msg': "Error calling Envelopes:create: " + str(e)}
        
    status = r.status_code
    if (status != 201): 
        return ({'ok': False, 'msg': "Error calling DocuSign Envelopes:create, status is: " + str(status)})

    data = r.json()
    envelope_id = data['envelopeId']
    setup_output_dir(envelope_id)
    
    # Instructions for reading the email
    html =  "<h2>Signature request sent!</h2>" + \
            "<p>Envelope ID: " + envelope_id + "</p>" + \
            "<p>Signer: " + ds_signer1_name + "</p>" + \
            "<p>CC: " + ds_cc1_name + "</p>" + \
            "<h2>Next steps</h2>" + \
            "<h3>1. View the incoming notifications and documents</h3>" + \
            "<p><a href='" + ds_recipe_lib.get_base_url() + "/files/" + envelope_id_to_dir(envelope_id) + "'" + \
            "  class='btn btn-primary' role='button' target='_blank' style='margin-right:1.5em;'>" + \
            "View Notification Files</a> (A new tab/window will be used.)</p>" + \
            "<h3>2. Respond to the Signature Request</h3>"

    ds_signer1_email_access = ds_recipe_lib.get_temp_email_access(ds_signer1_email)
    if (ds_signer1_email_access):
        # A temp account was used for the email
        html += "<p>Respond to the request via your mobile phone by using the QR code: </p>" + \
                "<p>" + ds_recipe_lib.get_temp_email_access_qrcode(ds_signer1_email_access) + "</p>" + \
                "<p> or via <a target='_blank' href='" + ds_signer1_email_access + "'>your web browser.</a></p>"
    else:
        # A regular email account was used
        html += "<p>Respond to the request via your mobile phone or other mail tool.</p>" + \
                "<p>The email was sent to " + ds_signer1_name + " &lt;" + ds_signer1_email + "&gt;</p>"

    html += "<p>Webhook url: " + webhook_url + "</p>"

    return {"ok": True,
        "envelope_id": envelope_id,
        "ds_signer1_email": ds_signer1_email,
        "ds_signer1_name": ds_signer1_name,
        "ds_signer1_access": ds_signer1_email_access,
        "ds_signer1_qr": ds_signer1_email,
        "ds_cc1_email": ds_cc1_email,
        "ds_cc1_name": ds_cc1_name,
        "webhook_url": webhook_url,
        "html": html
    }


########################################################################
########################################################################

def    setup_output_dir(envelope_id):
# setup output dir for the envelope
    # Store the file. Create directories as needed
    # Some systems might still not like files or directories to start with numbers.
    # So we prefix the envelope ids with E and the timestamps with T
    
    # Make the envelope's directory
    
    envelope_dir = get_envelope_dir(envelope_id)
    os.makedirs(envelope_dir)
    # and copy in the ReadMe file
    files_dir = os.path.join(os.getcwd(), xml_file_dir)
    shutil.copy(os.path.join(files_dir, readme), envelope_dir)

def    get_envelope_dir(envelope_id):
    # Some systems might still not like files or directories to start with numbers.
    # So we prefix the envelope ids with E
    
    # Make the envelope's directory
    files_dir = os.path.join(os.getcwd(), xml_file_dir)
    envelope_dir = os.path.join(files_dir, envelope_id_to_dir(envelope_id))
    return envelope_dir

def envelope_id_to_dir(envelope_id):
    return "E" + envelope_id

########################################################################
########################################################################

def webhook_listener():
    # Process the incoming webhook data. See the DocuSign Connect guide
    # for more information
    #
    # Strategy: examine the data to pull out the envelope_id and time_generated fields.
    # Then store the entire xml on our local file system using those fields.
    #
    # If the envelope status=="Completed" then store the files as doc1.pdf, doc2.pdf, etc
    #
    # This function could also enter the data into a dbms, add it to a queue, etc.
    # Note that the total processing time of this function must be less than
    # 100 seconds to ensure that DocuSign's request to your app doesn't time out.
    # Tip: aim for no more than a couple of seconds! Use a separate queuing service
    # if need be.
    data = request.data # This is the entire incoming POST content.
                        # This is dependent on your web server. In this case, Flask
      
    # f = open(os.getcwd() + "/app/example_completed_notification.xml")
    # data = f.read()
                      
    # Note, there are many options for parsing XML in Python
    # For this recipe, we're using Beautiful Soup, http://www.crummy.com/software/BeautifulSoup/

    xml = BeautifulSoup(data, "xml")
    envelope_id = xml.EnvelopeStatus.EnvelopeID.string
    time_generated = xml.EnvelopeStatus.TimeGenerated.string

    # Store the file.     
    # Some systems might still not like files or directories to start with numbers.
    # So we prefix the envelope ids with E and the timestamps with T
    envelope_dir = get_envelope_dir(envelope_id)
    filename = "T" + time_generated.replace(':' , '_') + ".xml" # substitute _ for : for windows-land
    filepath = os.path.join(envelope_dir, filename)
    with open(filepath, "w") as xml_file:
        xml_file.write(data)
    
    # If the envelope is completed, pull out the PDFs from the notification XML
    if (xml.EnvelopeStatus.Status.string == "Completed"):
        # Loop through the DocumentPDFs element, storing each document.
        for pdf in xml.DocumentPDFs.children:
            if (pdf.DocumentType.string == "CONTENT"):
                filename = 'Completed_' + pdf.Name.string
            elif (pdf.DocumentType.string == "SUMMARY"):
                filename = pdf.Name.string
            else:
                filename = pdf.DocumentType.string + "_" + pdf.Name.string
            full_filename = os.path.join(envelope_dir, filename)
            with open(full_filename, "wb") as pdf_file:
                pdf_file.write(base64.b64decode(pdf.PDFBytes.string))


########################################################################
########################################################################

def nda_fields():
    # The fields for the sample document "NDA"
    # Create 4 fields, using anchors 
    #   * signer1sig
    #   * signer1name
    #   * signer1company
    #   * signer1date
    fields = {
    "signHereTabs": [{
        "anchorString": "signer1sig",
        "anchorXOffset": "0",
         "anchorYOffset": "0",
        "anchorUnits": "mms",
        "recipientId": "1",
        "name": "Please sign here",
        "optional": "false",
        "scaleValue": 1,
        "tabLabel": "signer1sig"}],
    "fullNameTabs": [{
        "anchorString": "signer1name",
         "anchorYOffset": "-6",
        "fontSize": "Size12",
        "recipientId": "1",
        "tabLabel": "Full Name",
        "name": "Full Name"}],
    "textTabs": [{
        "anchorString": "signer1company",
         "anchorYOffset": "-8",
        "fontSize": "Size12",
        "recipientId": "1",
        "tabLabel": "Company",
        "name": "Company",
        "required": "false"}],
    "dateSignedTabs": [{
        "anchorString": "signer1date",
         "anchorYOffset": "-6",
        "fontSize": "Size12",
        "recipientId": "1",
        "name": "Date Signed",
             "tabLabel": "Company"}]
    }
    return fields

########################################################################
########################################################################

# FIN
    















