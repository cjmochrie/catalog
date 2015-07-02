http://52.26.156.209/
port 2200

http://52.26.156.209/catalog/

Below are the steps I took setting the server up:
3rd party software (not including python packages)
Fail2Ban
postgresql postgresql-contrib
virtualenv
apache2
apache2-dev
apache2-mpm-worker
libapache2-mod-wsgi

Config changes:
Added user grader (password in instructor notes)
SSH port 20 -> 2200
firewall allowing 80, 2200, 123
Changed LogLevel for SSH to VERBOSE
Increased Fail2Ban maxretry to 5
Disabled root login
Created key pair for user grader
Configured weekly security updates and periodic deletion of security update log files
Changed hostname to 'udacity'
Changed timezone to UTC (was already UTC though)
Created postgresql user 'catalog' with password same as grader
Created postgresql database 'catalog'
Configured apache2 server to not autoindex



Login to server
ssh -i udacity_key.rsa root@52.11.42.236

update
bash: apt-get update
bash: apt-get upgrade

Add user
switch to root
bash: adduser grader ---- enter 'SEE NTOES' for password
bash: visudo  then add grader ALL=(ALL:ALL) ALL
bash: adduser grader sudo

Change SSH Port and Configure Firewall
edit /etc/ssh/sshd_config change 'Port 20' to 'Port 2200' beneath '#What ports, IPs and protocols we listen for'
bash: nano /etc/ssh/sshd_config - change 'LogLevel INFO' to 'LogLevel VERBOSE'
bash: ufw allow 80
bash: ufw allow 2200
bash: ufw allow 123
bash: ufw enable
bash: reboot

reconnect
ssh -i udacity_key.rsa root@52.11.42.236  -p 2200

Configure SSH for new user
bash: nano /etc/ssh/sshd_config - change 'LogLevel INFO' to 'LogLevel VERBOSE'
bash: su grader
(make sure in home directory)
bash: mkdir .ssh
bash: chmod 700 .ssh
bash: ssh-keygen -t rsa
(copy private key to home computer - make sure public key is saved in authorized_keys inside .ssh directory just created
now should be able to login in with ssh -i my_key.rsa grader@xy.ab.yyy.zzz

Disable remote root login
bash: sudo nano /etc/ssh/sshd_config - change 'PermitRootLogin abcdefg' to 'PermitRootLogin no'
bash: sudo service ssh restart

Configure Fail2Ban
bash: sudo apt-get install fail2ban
bash: sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
bash: sudo nano /etc/fail2ban/jail.local - change 'maxretry' to 5
bash: sudo service fail2ban stop
bash: sudo service fail2ban start

Configure automatic updates
bash: sudo nano /etc/cron.weekly/apt-security-updates - copy in: 
'
echo "**************" >> /var/log/apt-security-updates
date >> /var/log/apt-security-updates
aptitude update >> /var/log/apt-security-updates
aptitude safe-upgrade -o Aptitude::Delete-Unused=false --assume-yes --target-release `lsb_release -cs`-security >> /var/log/apt-security-updates
echo "Security updates (if any) installed"
'
bash: sudo chmod +x /etc/cron.weekly/apt-security-updates
bash: sudo nano /etc/logrotate.d/apt-security-updates - copy in:
     '
       /var/log/apt-security-updates {
        rotate 2
        weekly
        size 250k
        compress
        notifempty
     }
     '

Change hostname
bash: hostnamectl set-hostname new-hostname
edit /etc/hosts after 127.0.0.1 to new-hostname
bash: reboot


Change timezones
dpkg-reconfigure tzdata  select 'None of the Above' then 'UTC'


Set up postgresql
bash: apt-get install postgresql postgresql-contrib
bash: apt-get install python-dev
bash: apt-get install python-psycopg2
bash: apt-get install libpq-dev
bash: sudo -u postgres psql postgres
     \password postgres - enter password SEE NOTES
edit: /etc/postgresql/9.3/main/pg_hba.conf change METHOD to md5 for 'local Unix domain socket connections'
bash: sudo /etc/init.d/postgresql restart
bash: sudo -u postgres createuser -D -A -P catalog with password: SEE NOTES
bash: sudo -u postgres createdb -O catalog catalog
bash: sudo /etc/init.d/postgresql restart


clone catalog
install pip, install virtualenv, create venv, install modules
bash: sudo apt-get install python-pip 
bash: sudo pip install virtualenv 
bash: sudo apt-get install git
bash: sudo mkdir vagrant
bash: cd vagrant
bash: sudo git clone https://github.com/cjmochrie/catalog.git


----inside catalog directory----
bash: sudo virtualenv venv
bash: source venv/bin/activate 
bash: sudo pip install Flask
bash: sudo pip install flask-seasurf
bash: sudo pip install httplib2
bash: sudo pip install dict2xml
bash: sudo pip install sqlalchemy
bash: sudo pip install oauth2client
bash: sudo pip install psycopg2
bash: sudo pip install requests
bash: sudo python populate_db.py
bash: deactivate

Change permitted address on Google developers tab, copy into client_secrets.json - doesn't work due to IP address not URL

Install and configure Apache2
bash: sudo apt-get install apache2
bash: sudo apt-get install apache2-dev
bash: sudo apt-get install apache2-mpm-worker
bash: sudo apt-get install libapache2-mod-wsgi python-dev
bash: sudo nano /etc/apache2/sites-available/catalog.conf and input below

<VirtualHost *:80>
                ServerName catalog.com
                ServerAdmin cameron.mochrie@gmail.com

              WSGIDaemonProcess catalog python-path=/var/www/catalog:/vagrant/catalog/venv/lib/python2.7/site-packages
              WSGIProcessGroup catalog
                WSGIScriptAlias / /var/www/catalog/catalog.wsgi
                <Directory /var/www/catalog/catalog/>
                        Order allow,deny
                        Allow from all
                </Directory>
                Alias /static /var/www/catalog/catalog/static
                <Directory /var/www/catalog/catalog/static/>
                        Order allow,deny
                        Allow from all
                </Directory>

                 Alias /templates /var/www/catalog/catalog/templates
                 <Directory /var/www/catalog/catalog/templates/>
                         Order allow,deny
                         Allow from all
                 </Directory>

                ErrorLog ${APACHE_LOG_DIR}/error.log
                LogLevel warn
                CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
bash: sudo a2enmod wsgi
bash: sudo a2dismod autoindex


Disable default site
bash: a2dissite 000-default
bash: sudo service apache2 reload

Move files around
bash: cd /var/www
bash: sudo mkdir catalog
bash:  sudo cp /vagrant/catalog/catalog.wsgi /var/www/catalog/catalog.wsgi
bash: cd catalog
bash: sudo mkdir catalog
bash: sudo cp -avr /vagrant/catalog/catalog/templates /var/www/catalog/catalog/templates
bash: sudo cp -avr /vagrant/catalog/catalog/static /var/www/catalog/catalog/static
bash: cd /var/www/catalog/catalog/static
bash: sudo rm client_secrets.json

Enable catalog
bash: sudo a2ensite catalog
bash: sudo service apache2 reload



Sources:

rename server http://askubuntu.com/questions/87665/how-do-i-change-the-hostname-without-a-restart 
postgresql listen to udacity https://github.com/PostgresApp/PostgresApp/issues/200 
https://computernerddiaries.wordpress.com/2014/10/24/erroryou-need-to-install-postgresql-server-dev-x-y-for-building-a-server-side-extension-or-libpq-dev-for-building-a-client-side-application/
https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps
http://stackoverflow.com/questions/11136913/disable-directory-listing-on-apache-but-access-to-individual-files-should-be-al
https://help.ubuntu.com/community/SSH/OpenSSH/InstallingConfiguringTesting
http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/managing-users.html
https://www.digitalocean.com/community/tutorials/how-to-install-and-use-fail2ban-on-ubuntu-14-04
https://help.ubuntu.com/community/AutomaticSecurityUpdates
