from datetime import datetime, timedelta 
import sys
from bs4 import BeautifulSoup
import boto3 
import json 
from botocore.exceptions import ClientError
import imaplib
import email
import email.header
import psycopg2
from config import EMAIL_ACCOUNT,EMAIL_PASSWORD,BUCKET,DATA_FOLDER,EMAIL_FOLDER
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

# conn = psycopg2.connect("host=localhost dbname=emails user=huy")
# cur = conn.cursor()
# cur.execute(emailTable_create)

KEY = "key_" + datetime.now().strftime("%d_%b_%Y")
FILENAME = "email_harry_" + \
	datetime.now().strftime("%d_%b_%Y") + ".csv"

def extract_text(body):
    soup = BeautifulSoup(body)
    # get text
    text = soup.get_text()

    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = ' .'.join(chunk for chunk in chunks if chunk)

    return text 

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


def process_mailbox(**kwargs):
    """
    Extract body, header, sender and date from each email 
    """

    list_email = [] 

    M = imaplib.IMAP4_SSL('imap.gmail.com')

    try:
        rv, data = M.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    except imaplib.IMAP4.error:
        print ("LOGIN FAILED!!! ")
        sys.exit(1)
    
    rv, data = M.select(kwargs['email_folder'])
    if rv == 'OK':
        rv, data = M.search(None, "ALL")
        if rv != 'OK':
            print("No messages found!")


        print(len(data[0].split()))
        num_id = 0

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
                    local_date = datetime.fromtimestamp(
                        email.utils.mktime_tz(date_tuple))
                    local_date = local_date.strftime("%d-%b-%Y")
                    print("Local Date:",local_date)
                else:
                    local_date = 'None'
                
                line = subject + "," + sender + "," +local_date
                print(line)
                list_email.append({'id': num_id,'body': body,'header': subject,'sender': sender,'date':local_date})
                num_id = num_id + 1
    else:
        print("ERROR: Unable to open mailbox ", rv)
    M.logout()
        
    return list_email 

# def extract_email(**kwargs):

#     save_file = kwargs['save_file']

#     # Use 'INBOX' to read inbox.  Note that whatever folder is specified,
#     # after successfully running this script all emails in that folder
#     # will be marked as read.
#     EMAIL_FOLDER = '"[Gmail]/Starred"'

#     M = imaplib.IMAP4_SSL('imap.gmail.com')

#     try:
#         rv, data = M.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
#     except imaplib.IMAP4.error:
#         print ("LOGIN FAILED!!! ")
#         sys.exit(1)

#     print(rv, data)

#     rv, mailboxes = M.list()
#     if rv == 'OK':
#         print("Mailboxes:")
#         print(mailboxes)

#     rv, data = M.select(EMAIL_FOLDER)
#     if rv == 'OK':
#         print("Processing mailbox...\n")
#         process_mailbox(M,save_file)
#         M.close()
#     else:
#         print("ERROR: Unable to open mailbox ", rv)

#     M.logout()

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2020, 1, 1),
    'retry_delay': timedelta(minutes=5),
    'provide_context': True
}
# Using the context manager alllows you not to duplicate the dag parameter in each operator
dag = DAG('upload_s3', default_args=default_args, schedule_interval='@once')

def upload_file_S3(**kwargs):
    source = kwargs['source']
    bucket = kwargs['bucket']
    key = kwargs['key']
    list_email = kwargs['ti'].xcom_pull(task_ids='extract_mail')

    s3 = boto3.resource("s3")
    try:
        s3.Object(bucket, key).load()
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            s3Object = s3.Object(bucket, key)
            s3Object.put(
                Body=(bytes(json.dumps(list_email).encode('UTF-8')))
            )
        else:
            print(e)
    print("Object exists")

extract_mail_task = PythonOperator(
    task_id='extract_mail',
    python_callable=process_mailbox,
    provide_context=True,
    op_kwargs={'email_folder': EMAIL_FOLDER},
    dag=dag)

upload_file_task = PythonOperator(
    task_id='upload_file_s3',
    python_callable=upload_file_S3,
    op_kwargs={'bucket': BUCKET, 'key': KEY, 'source': FILENAME},
    dag=dag)

extract_mail_task >> upload_file_task