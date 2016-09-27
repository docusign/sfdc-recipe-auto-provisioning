# Create the Powerform

The DocuSign Powerform is used to initiate the partner agreement process which will culminate in the new partner being automatically added to your Salesforce Partner Community

In DocuSign, Powerforms are created *from* templates. So the first step is to create a template.

* This recipe includes a sample agreement file [`The World Wide Corp Partner Agreement.docx`](../app/static/sample_documents_master/World_Wide_Corp_Partner_Agreement.docx) Download the document to your computer.

* Login to your DocuSign demo (developer sandbox) account
* Click Templates
* Click New > Create Template
  * Name: World Wide Co Partner Agreement
  * Description: Powerform filled in by prospective partner
* Upload the Word document
* Set Recipients:
* Check Set Signing Order
* Recipient 1 - Role: "Partner"
* Recipient 2 - Role: [leave blank]. Use a DocuSign user name and email (from this account) for this recipient. 
  You can create a second user in your Developer account, or set yourself as the "Business Development group" signer. 
* Use this recipient's "gear" icon to open the recipient's advanced settings panel.
* On the panel, click both options:
    * Don't allow senders to edit recipient
    * Don't allow senders to delete recipient
    * Click Done
* Click the Next button 
* You now see the tagger screen.
* Add a text field for the Partner name:
    * Place the field by the partner name heading
    * Change Formatting > Size to 12
    * Change Data Label to pname
    * Make the field's width wider
* Add a text field for the Partner contact first name:
    * Place the field by the partner contact first name heading
    * Change Formatting > Size to 11
    * Change Data Label to pfname
    * Make the field's width wider
* Add Name field for the Partner contact last name:
    * Place the field by the partner contact last name heading
    * Change Formatting > Size to 11
    * Change Data Label to plname
    * Make the field's width wider
* Add signature field for the Partner:
    * Place the field by the partner signature heading
* Add date signed field for the Partner date:
    * Place the field by the partner date heading
    * Change Formatting > Size to 11
* Switch the "Add fields for" drop down menu at the top of the screen to the second signer
* Add signature field for World Wide Corp:
    * Place the field by the signature heading
    * Change Data Label to wsig
* Add date signed field for the World Wide Corp date:
    * Place the field by the date heading
    * Change Formatting > Size to 11
* Add text field for the Partner SFDC url:
    * Place the field by the heading
    * Change Formatting > Size to 12
    * Change Data Label to wpartner
    * Make the field's width wider
* Click Save and Close
* You will now see the list of templates for your account.
* Choose Use > Create Power Form for the template.
* The Create Powerform form is shown.
    * Add "To join the partner program, please fill in and sign the form." to the Instructions for Signers field
    * Use the default for the other entries in the form
    * Click Create
* You will receive a url for the Powerform. Make note of it since that url is used to start the process.

