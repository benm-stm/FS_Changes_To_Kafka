To launch and test the whole stack wich is composed by :
- 2 kafka, 1 zookeeper
- 1 NGINX (expose ressources)
- 1 python script who'll watch the file system and notify kafka every x second if there are changes
You need to run :
~~~~
docker-compose up
~~~~
Here is the nginx server conf

    server {
        listen       80;
        server_name  localhost;
        #access_log  logs/host.access.log  main;

        #here we have to create a persistent ressourcesvolume for /data
        root /data;
        location / {
            try_files $uri $uri/ =404;
        }

run consumer :
sudo docker-compose exec kafka_1 kafka-console-consumer.sh --bootstrap-server kafka_1:9092 --topic sftp
