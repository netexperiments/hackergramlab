#!/bin/bash

# Allow to be queries from outside
sed -i '31 s/bind-address/#bind-address/' /etc/mysql/mysql.conf.d/mysqld.cnf

service mysql start
service mongodb start

# Create a Database, a user with password, and permissions
cd /var/hackergram
mysql -u root < start.sql
ollama serve &
sleep 5
python3 /var/hackergram/hackergram.py &  
FLASK_PID=$! 

while true; do
    sleep 60
done
