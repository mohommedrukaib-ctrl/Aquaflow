# AquaFlow — Windows 24/7 Deployment Guide

## Requirements
- Windows 10/11 or Windows Server
- PostgreSQL 17 installed and running
- Python 3.13 installed
- NSSM (Non-Sucking Service Manager)

---

## Step 1: Install PostgreSQL as Windows Service

PostgreSQL installer automatically creates a service that starts with Windows.

Verify:

services.msc → Find "postgresql-x64-17"
Right-click → Properties → Startup type: Automatic

text


---

## Step 2: Install NSSM

Download: https://nssm.cc/download

Extract nssm.exe to `C:\nssm\`

Add to PATH:
- System Properties → Environment Variables → Path → Add `C:\nssm\win64`

---

## Step 3: Configure Waitress (WSGI Server)

Waitress is already installed in requirements.

Create `run_server.bat` in project root:

```bat
@echo off
cd /d "C:\AquaFlow"
call venv\Scripts\activate
python -m waitress --host=0.0.0.0 --port=8000 config.wsgi:application
Test it works manually first:

text

Double-click run_server.bat
Open browser: http://localhost:8000/
Step 4: Install as Windows Service
Open Command Prompt as Administrator:

cmd

nssm install AquaFlow
Configuration dialog appears:

Application tab:

Path: C:\AquaFlow\run_server.bat
Startup directory: C:\AquaFlow
Details tab:

Display name: AquaFlow
Description: AquaFlow Car Wash System
Startup type: Automatic
I/O tab:

Output: C:\AquaFlow\logs\service_out.log
Error: C:\AquaFlow\logs\service_err.log
Click Install service.

Step 5: Start the Service
cmd

nssm start AquaFlow
Or via services.msc → Find AquaFlow → Right-click → Start.

Step 6: Configure Windows Firewall
Open Command Prompt as Administrator:

cmd

netsh advfirewall firewall add rule name="AquaFlow" dir=in action=allow protocol=TCP localport=8000
Block direct PostgreSQL access from network:

cmd

netsh advfirewall firewall add rule name="Block PostgreSQL External" dir=in action=block protocol=TCP localport=5432
netsh advfirewall firewall add rule name="Allow PostgreSQL Local" dir=in action=allow protocol=TCP localport=5432 localip=127.0.0.1
Step 7: LAN Access
Find server IP:

cmd

ipconfig
Look for "IPv4 Address" (e.g., 192.168.1.100)

Access from other computers on network:

text

http://192.168.1.100:8000/
Step 8: Add ALLOWED_HOSTS
Edit C:\AquaFlow\.env:

text

ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.100
Add your server's IP address.

Restart service:

cmd

nssm restart AquaFlow
Step 9: Verify Auto-Start
Restart Windows:

cmd

shutdown /r /t 0
After Windows boots:

PostgreSQL service starts automatically
AquaFlow service starts automatically
Access http://192.168.1.100:8000/ from any computer
Managing the Service
cmd

nssm start AquaFlow     # Start
nssm stop AquaFlow      # Stop
nssm restart AquaFlow   # Restart
nssm status AquaFlow    # Check status
nssm remove AquaFlow    # Uninstall
View Logs
text

C:\AquaFlow\logs\aquaflow.log
C:\AquaFlow\logs\error.log
C:\AquaFlow\logs\service_out.log
C:\AquaFlow\logs\service_err.log
