FROM python:2.7.15-alpine3.6

#to inject vars to the python script try to define them as env vars
VOLUME watched_dir

COPY requirements.txt . 
RUN pip install -r requirements.txt

COPY kafka_fs_notifier.py .
CMD ["/kafka_fs_notifier.py"]
