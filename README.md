# DocuSign SFDC Recipe: Auto-provision Community Cloud Members

This repo contains a Python Flask application that demonstrates a Salesforce (SFDC) auto-provisioning use case:

* A company ("World Wide Co") uses Salesforce Community Cloud to host their partner community.
* When a prospective partner company wants to join World Wide Co's partner program, they click on a "Join the Partner Program" link on the World Wide Co website.
* The link opens a DocuSign PowerForm. The prospective partner enters their company name, their own name as the contact, and their own email.
* Using DocuSign, they review and then sign the partner agreement.
* DocuSign then routes the partner agreement to a specific contact in the Business Development (BizDev) department of World Wide Co. Or the template could be set up to use a Signing Group. Eg, the agreement could be sent to all of the Business Development representatives.
* The BizDev rep reviews the agreement and approves it. 
* He looks up the new partner in Salesforce to see if they already have a partner entry. He creates one if they don't.
* He enters the SFDC partner url into the DocuSign envelope and signs it.
* This software application receives a notification from DocuSign, using the Connect webhook feature, that the envelope was signed. 
* Using the SFDC REST API, this application provisions the new partner in the World Wide Co partner community. It first creates a contact record, then a partner community user record.
* Salesforce notifies the new partner that they can now login to the community.

## Try it on Heroku
Use the deploy button to immediately try this app on Heroku. You can use Heroku’s free service tier, no credit card is needed.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

Note: during the Heroku *build* process, the setup.py step for **lxml** takes several minutes since it includes a compilation.

## Run the app locally

1. Install a recent version of Python 2.x, eg 2.7.11 or later.
1. Install pip
1. Clone this repo to your computer
1. `cd` to the repo’s directory
1. `pip install -r requirements.txt` # installs the application’s requirements
1. `python run.py` # starts the application on port 5000
1. Use a browser to load [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## Have a question? Pull request?
If you have a question about the Signature REST API, please use StackOverflow and tag your question with `docusignapi`

For bug reports and pull requests, please use this repo’s issues page.
