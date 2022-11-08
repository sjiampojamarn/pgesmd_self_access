#! /bin/bash

mkdir -p /root/auth
chmod -R 600 /root/auth

mkdir -p /root/data/espi_xml/
cd /root

python3 --version
python3 /pgesmd/SelfAccessServer.py
