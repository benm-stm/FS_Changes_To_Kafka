#!/usr/bin/env python

import os
import copy
import threading, logging, time
from threading import Timer,Thread,Event
from kafka import KafkaProducer
import json
import csv
from pwd import getpwuid
import filecmp
import uuid

class File(object):
    def __init__(self, data, csv_path, web_server_url):
        self.data = data
        self.csv_path = csv_path
        self.web_server_url = web_server_url

    def construct_csv_line(self):
        with open(self.csv_path, "wb") as csv_file:
            writer = csv.writer(csv_file, delimiter=';')
            for line in self.data:
                writer.writerow(self.file_infos_into_array(line))

    def file_infos_into_array(self, path_to_file):
        return self.web_server_url+path_to_file, self.find_nature(path_to_file), self.find_owner(path_to_file), self.modification_date(path_to_file)

    def find_owner(self, path_to_file):
        return getpwuid(os.stat(path_to_file).st_uid).pw_name

    def find_nature(self, path_to_file):
        if os.path.isdir(path_to_file):
            return 'folder'
        return 'file'

    def modification_date(self, path_to_file):
        return os.stat(path_to_file).st_mtime


class Watcher():
    def __init__(self, watched_dir, web_server_url, kafka_url, kafka_topic_name, export_csv_path, kafka_producer_threshold_time, kafka_index, kafka_event_name, kafka_json_version):
        self.watched_dir = watched_dir
        self.web_server_url = web_server_url
        self.kafka_url = kafka_url
        self.kafka_topic_name = kafka_topic_name
        self.kafka_producer_threshold_time = kafka_producer_threshold_time
        self.kafka_index = kafka_index
        self.kafka_event_name = kafka_event_name
        self.kafka_json_version = kafka_json_version
        self.export_csv_path = export_csv_path

        #init timer
        self.timer = Kafka_timer(self.kafka_producer_threshold_time, self.isThresholdF)
        self.timer.start()

    def isThresholdF(self):
        logging.debug("timer hit 0")
        if not self.hasSameContent() :
            logging.info("FS updated")
            self.infos_for_kafka()

    def hasSameContent(self):
        old_fs_tree = self.export_csv_path + '.old'
        if os.path.isfile(old_fs_tree):
            os.remove(old_fs_tree)
        if os.path.isfile(self.export_csv_path):
            os.rename(self.export_csv_path, old_fs_tree)
        else :
            open(old_fs_tree, 'a').close()
        fs_data = self.discover_tree_with_files(self.watched_dir, True)
        File(fs_data, self.export_csv_path, self.web_server_url).construct_csv_line()
        return filecmp.cmp(self.export_csv_path, old_fs_tree) 

    def discover_tree_with_files(self, dir_path, with_files):
        fs_tree_array = []
        for dirpath, dirs, files in os.walk(dir_path):
            fs_tree_array.append(dirpath)
            if with_files:
                for file in files:
                    fs_tree_array.append(dirpath+'/'+file)
        return fs_tree_array

    def infos_for_kafka(self):
        json_data = self.json_formatter_to_kafka()
        logging.debug("Json to kafka content: " + str(json_data))
        Kafka_producer(self.kafka_url, self.kafka_topic_name).run(json_data)

    def json_formatter_to_kafka(self):
        data = {}
        data['id'] = uuid.uuid4().hex
        data['operation'] = 'change'
        data['path'] = self.export_csv_path

        links ={}
        links['self'] = self.web_server_url + self.export_csv_path
        
        version = {}
        version[self.kafka_json_version] = data
        version['links'] = links

        body = {}
        body['body'] = version

        msg = {}
        msg['index'] = self.kafka_index 
        msg['event'] = self.kafka_event_name
        msg['body'] = body 
        return json.dumps(msg)

class Kafka_producer(threading.Thread):
    def __init__(self, kafka_url, kafka_topic_name):
        self.kafka_url = kafka_url
        self.kafka_topic_name = kafka_topic_name
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self, json_data):
        producer = KafkaProducer(bootstrap_servers=self.kafka_url)
        producer.send(self.kafka_topic_name, json_data)
        producer.close()

class Kafka_timer():
   def __init__(self,sec,function_to_call):
      self.sec=sec
      self.function_to_call = function_to_call
      self.thread = Timer(self.sec,self.handle_function)

   def handle_function(self):
      self.function_to_call()
      self.thread = Timer(self.sec,self.handle_function)
      self.thread.start()

   def start(self):
      self.thread.start()

   def cancel(self):
      self.thread.cancel()

def main():
    #params
    watched_dir = os.getenv('WATCHED_ROOT_DIR', '/watched_dir')
    webserver_url = os.getenv('WEBSERVER_URL', '127.0.0.1:9000')
    kafka_url = os.getenv('KAFKA_URL', 'kafka:9092')
    kafka_topic_name = os.getenv('KAFKA_TOPIC', 'topic')
    kafka_index = os.getenv('KAFKA_INDEX', '-1')
    kafka_json_version = os.getenv('KAFKA_JSON_VERSION', '1')
    kafka_event_name = os.getenv('KAFKA_EVENT_NAME', 'sftp/files-list/updated')
    export_csv_path = os.getenv('EXPORT_CSV_PATH', '/exports')
    export_csv_path = export_csv_path + '/' + 'fs_tree.csv'
    #time in which the producer will send data to kafka when it hits 0 (last action done is issue in at least n sec)
    kafka_producer_threshold_time = int(float(os.getenv('KAFKA_PRODUCER_THRESHOLD_TIME', 5)))

    #begin the watch
    Watcher(watched_dir, webserver_url, kafka_url, kafka_topic_name, export_csv_path, kafka_producer_threshold_time, kafka_index, kafka_event_name, kafka_json_version)

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
        level=logging.DEBUG
        )
    main()
