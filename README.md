to launch the stack:
~~~~
mkdir -p /data/exports
mkdir /data/watched_dir
docker-compose up
~~~~

here is the nginx server conf

    server {
        listen       80;
        server_name  localhost;
        #access_log  logs/host.access.log  main;

        #here we have to create a persistent ressourcesvolume for /data
        root /data;
        location / {
            try_files $uri $uri/ =404;
        }

to run the kafka consumer to see forwarded jsons to kafka:
~~~~
sudo docker-compose exec kafka_1 kafka-console-consumer.sh --bootstrap-server kafka_1:9092 --topic sftp
~~~~
