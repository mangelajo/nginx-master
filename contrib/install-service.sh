#!/bin/sh
sudo cp contrib/nginx-master.service /etc/systemd/system
sudo chmod 664 /etc/systemd/system/nginx-master.service
sudo mkdir /etc/nginx-master
sudo touch /etc/nginx-master/nginx-master.conf
sudo systemctl daemon-reload
sudo service nginx-master start
sudo service nginx-master status
