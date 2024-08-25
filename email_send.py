
# Amazon SES
from email.utils import formataddr
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from datetime import datetime

import configparser



def get_sending_creds():
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    creds = {
        'smtp_server': config['DEFAULT'].get('smtpserver', ''),
        'smtp_port': config['DEFAULT'].get('smtpport', ''),
        'smtp_username': config['DEFAULT'].get('smtpuser', ''),
        'smtp_password': config['DEFAULT'].get('smtppass', ''),
        'send_from': config['DEFAULT'].get('sendfrom', ''),
        'send_to': config['DEFAULT'].get('sendto', '')
    }
    
    return creds

def email_html(printer_name, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Printer Status</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji';
            line-height: 1.5;
            color: #24292f;
            background-color: #ffffff;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #24292f;
            color: #ffffff;
            padding: 16px;
            border-radius: 6px 6px 0 0;
        }
        .content {
            background-color: #f6f8fa;
            border: 1px solid #d0d7de;
            border-radius: 0 0 6px 6px;
            padding: 20px;
        }
        h1, h2 {
            margin-top: 0;
        }
        .button-3 {
            appearance: none;
            background-color: #2ea44f;
            border: 1px solid rgba(27, 31, 35, .15);
            border-radius: 6px;
            box-shadow: rgba(27, 31, 35, .1) 0 1px 0;
            box-sizing: border-box;
            color: #fff;
            cursor: pointer;
            display: inline-block;
            font-family: -apple-system,system-ui,"Segoe UI",Helvetica,Arial,sans-serif,"Apple Color Emoji","Segoe UI Emoji";
            font-size: 14px;
            font-weight: 600;
            line-height: 20px;
            padding: 6px 16px;
            position: relative;
            text-align: center;
            text-decoration: none;
            user-select: none;
            -webkit-user-select: none;
            touch-action: manipulation;
            vertical-align: middle;
            white-space: nowrap;
        }
        .button-3:hover {
            background-color: #2c974b;
        }
        .button-3:focus {
            box-shadow: rgba(46, 164, 79, .4) 0 0 0 3px;
            outline: none;
        }
        .button-3:active {
            background-color: #298e46;
            box-shadow: rgba(20, 70, 32, .2) 0 1px 0 inset;
        }
        .button-4 {
            appearance: none;
            background-color: #FAFBFC;
            border: 1px solid rgba(27, 31, 35, 0.15);
            border-radius: 6px;
            box-shadow: rgba(27, 31, 35, 0.04) 0 1px 0, rgba(255, 255, 255, 0.25) 0 1px 0 inset;
            box-sizing: border-box;
            color: #24292E;
            cursor: pointer;
            display: inline-block;
            font-family: -apple-system, system-ui, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
            font-size: 14px;
            font-weight: 500;
            line-height: 20px;
            list-style: none;
            padding: 6px 16px;
            position: relative;
            transition: background-color 0.2s cubic-bezier(0.3, 0, 0.5, 1);
            user-select: none;
            -webkit-user-select: none;
            touch-action: manipulation;
            vertical-align: middle;
            white-space: nowrap;
            word-wrap: break-word;
        }
        .button-4:hover {
            background-color: #F3F4F6;
            text-decoration: none;
            transition-duration: 0.1s;
        }
        .button-4:active {
            background-color: #EDEFF2;
            box-shadow: rgba(225, 228, 232, 0.2) 0 1px 0 inset;
            transition: none 0s;
        }
        .button-4:focus {
            outline: 1px transparent;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>3D Printer Status Update</h1>
        </div>
        <div class="content">
            <h1>""" + message + """</h1>
            <h2>""" + printer_name + """</h2>
            <p><strong>Completed at:</strong> <span id="timestamp">""" + timestamp + """</span></p>
            <p><strong>Message:</strong> <span id="message">""" + message + """</span></p>
            
        </div>
    </div>

    
</body>
</html>
"""

def send_email(printer_name, message):
    msg = MIMEMultipart('alternative')
    if get_sending_creds()['send_from'] != '':
        msg['From'] = formataddr(("3D Printer Status", get_sending_creds()['send_from']))
    else:
        return
    msg['To'] = get_sending_creds()['send_to']
    msg['Subject'] = printer_name + ' - ' + message
    html = email_html(printer_name, message)
    
    part = MIMEText(html, 'html')
    msg.attach(part)
    mailserver = smtplib.SMTP(get_sending_creds()['smtp_server'],get_sending_creds()['smtp_port'])
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    mailserver.login(get_sending_creds()['smtp_username'], get_sending_creds()['smtp_password'])
    mailserver.sendmail(get_sending_creds()['send_from'], get_sending_creds()['send_to'], msg.as_string())
    mailserver.quit()

    
