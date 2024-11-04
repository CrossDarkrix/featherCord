#!/bin/bash
echo "downloading featherCord command....."
wget https://raw.githubusercontent.com/CrossDarkrix/featherCord/main/servers/featherCord
chmod +x featherCord
echo "downloading background running command....."
wget https://raw.githubusercontent.com/CrossDarkrix/featherCord/main/servers/_featherCord
chmod +x _featherCord
echo "running featherCord!"
./featherCord