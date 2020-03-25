from datetime import datetime, timedelta 
from app import extract_email
from config import BUCKET,DATA_FOLDER
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

KEY = "key_" + datetime.now().strftime("%d_%b_%Y")
FILENAME = "email_harry_" + \
	datetime.now().strftime("%d_%b_%Y") + ".csv"

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2020, 1, 1),
    'retry_delay': timedelta(minutes=5)
}
# Using the context manager alllows you not to duplicate the dag parameter in each operator
dag = DAG('upload_s3', default_args=default_args, schedule_interval='@once')


def upload_file_S3(source, bucket, key):
    s3 = boto3.resource("s3")
    try:
        s3.Object(bucket, key).load()
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            s3.upload_file(source, bucket, key)
        else:
            print(e)
    print("Object exists")

extract_mail_task = PythonOperator(
    task_id='extract_mail',
    python_callable=extract_email,
    op_kwargs={'save_file': DATA_FOLDER + FILENAME},
    dag=dag)

upload_file_task = PythonOperator(
    task_id='upload_file_s3',
    python_callable=upload_file_S3,
    op_kwargs={'bucket': BUCKET, 'key': KEY, 'source': DATA_FOLDER + FILENAME},
    dag=dag)

extract_mail_task >> upload_file_task