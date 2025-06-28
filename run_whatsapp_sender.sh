#!/bin/bash

echo "Installing required packages..."
pip3 install flask selenium pandas webdriver-manager

echo "Starting WhatsApp Bulk Sender..."
python3 whatsapp_sender_app.py

# Keep terminal open
read -p "Press Enter to exit..."