from config import ACCESS_KEY,SECRET_KEY
import boto3
from botocore.exceptions import ClientError
import logging 

s3 = boto3.client("s3")

bucket_name = "email-collector-harry"

try:
    with open('sample.txt', 'rb') as data:
        s3.upload_fileobj(data, bucket_name, 'filenameintos3.txt')

except ClientError as e:
    logging.error(e)

