#!/usr/bin/env python
#
# Very basic example of using Python 3 and IMAP to iterate over emails in a
# gmail folder/label.  This code is released into the public domain.
#
# This script is example code from this blog post:
# http://www.voidynullness.net/blog/2013/07/25/gmail-email-with-python-via-imap/
#
# This is an updated version of the original -- modified to work with Python 3.4.
#
import sys
from config import EMAIL_ACCOUNT,EMAIL_PASSWORD
import imaplib
import getpass
import email
import email.header
import datetime
import pandas as pd 
from helper import extract_text
import boto3 
from botocore.exceptions import ClientError

filename = "email_harry_" + \
    datetime.datetime.now().strftime("%d_%b_%Y") + ".csv"

data_folder = "data/"

def get_body_email(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))

            # skip any text/plain (txt) attachments
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                body = part.get_payload(decode=True)  # decode
                break
    # not multipart - i.e. plain text, no attachments, keeping fingers crossed
    else:
        body = msg.get_payload(decode=True)
    return body


def process_mailbox(M,save_file):
    """
    Extract body, header, sender and date from each email 
    """

    list_email = [] 

    rv, data = M.search(None, "ALL")
    if rv != 'OK':
        print("No messages found!")
        return

    print(len(data[0].split()))

    for num in data[0].split():

            rv, data = M.fetch(num, '(RFC822)')
            if rv != 'OK':
                print("ERROR getting message", num)
                return
            msg = email.message_from_bytes(data[0][1])

            body = extract_text(get_body_email(msg))

            subject = str(email.header.make_header(email.header.decode_header(msg['Subject'])))
            
            sender = str(email.header.make_header(email.header.decode_header(msg['From'])))

            print('Message %s: %s' % (num, subject))
            print('Raw Date:', msg['Date'])
            # Now convert to local date-time
            date_tuple = email.utils.parsedate_tz(msg['Date'])
            print(date_tuple)
            if date_tuple:
                local_date = datetime.datetime.fromtimestamp(
                    email.utils.mktime_tz(date_tuple))
                local_date = local_date.strftime("%d-%b-%Y")
                print("Local Date:",local_date)
            else:
                local_date = 'None'
            
            line = subject + "," + sender + "," +local_date
            print(line)
            list_email.append({'Content': body,'Subject': subject,'Sender': sender,'Date':local_date})
    
    df = pd.DataFrame(list_email)
    df.to_csv(save_file,index=False)

def extract_email(save_file):

    # Use 'INBOX' to read inbox.  Note that whatever folder is specified,
    # after successfully running this script all emails in that folder
    # will be marked as read.
    EMAIL_FOLDER = '"[Gmail]/Starred"'

    M = imaplib.IMAP4_SSL('imap.gmail.com')

    try:
        rv, data = M.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    except imaplib.IMAP4.error:
        print ("LOGIN FAILED!!! ")
        sys.exit(1)

    print(rv, data)

    rv, mailboxes = M.list()
    if rv == 'OK':
        print("Mailboxes:")
        print(mailboxes)

    rv, data = M.select(EMAIL_FOLDER)
    if rv == 'OK':
        print("Processing mailbox...\n")
        process_mailbox(M,save_file)
        M.close()
    else:
        print("ERROR: Unable to open mailbox ", rv)

    M.logout()



