## HTTPS Setup

Jenkins HTTPS access requires creating a keystore and configuring the Jenkins systemd service. Two certificate approaches are covered below: Let's Encrypt (recommended for instances with a public domain name) and self-signed certificates (for internal or testing use).

---

### Let's Encrypt — New Certificate

Ports 80 and 443 must be open on the instance security group for the ACME challenge.

Access the main node via Session Manager, then install certbot and generate certificates. On Amazon Linux 2023, certbot must be installed via `pip3`.

```bash
sudo pip3 install certbot
sudo certbot certonly --standalone
```

You'll be prompted for your email address, Terms of Service acceptance, and the full domain name of your Jenkins instance (e.g. `jenkins.fortinetcloudcse.com`).

Once complete, certs are at `/etc/letsencrypt/live/<your-domain>/`.

Create a working directory, copy the certs, and set a keystore passphrase:

```bash
sudo mkdir -p /var/lib/jenkins/.ssl
sudo chown jenkins:jenkins /var/lib/jenkins/.ssl
sudo cp /etc/letsencrypt/live/<your-domain>/* /var/lib/jenkins/.ssl
sudo su jenkins -s /bin/bash
echo my-P@ssw0rd > /var/lib/jenkins/.ssl/passphrase.txt
```

Create the PKCS12 archive:

```bash
cd /var/lib/jenkins/.ssl
openssl pkcs12 -export -out jenkins.p12 \
  -passout 'file:passphrase.txt' -inkey privkey.pem -in fullchain.pem
```

Create the Jenkins keystore from the archive:

```bash
keytool -importkeystore -srckeystore jenkins.p12 \
  -srcstorepass:file passphrase.txt -srcstoretype PKCS12 \
  -destkeystore jenkins.jks -deststorepass:file passphrase.txt
```

Copy the keystore and set permissions (exit the Jenkins user shell first to run as ssm-user):

```bash
sudo mkdir -p /etc/jenkins
sudo cp /var/lib/jenkins/.ssl/jenkins.jks /etc/jenkins
sudo chown -R jenkins:jenkins /etc/jenkins
sudo chmod 700 /etc/jenkins
sudo chmod 600 /etc/jenkins/jenkins.jks
```

Create the systemd override:

```bash
sudo mkdir -p /etc/systemd/system/jenkins.service.d
sudo cat << EOF > /etc/systemd/system/jenkins.service.d/override.conf
[Service]
Environment="JENKINS_PORT=-1"
Environment="JENKINS_HTTPS_PORT=8443"
Environment="JENKINS_HTTPS_KEYSTORE=/etc/jenkins/jenkins.jks"
Environment="JENKINS_HTTPS_KEYSTORE_PASSWORD=my-P@ssw0rd"
Environment="JENKINS_HTTPS_LISTEN_ADDRESS=0.0.0.0"
EOF
sudo systemctl daemon-reload
sudo systemctl restart jenkins
```

Jenkins is now accessible at `https://<your-domain>:8443`.

---

### Let's Encrypt — Certificate Renewal

Port 80 must be open on the security group during renewal.

```bash
sudo certbot renew --dry-run   # verify renewal would succeed
sudo certbot renew
```

If renewal succeeds, reimport the updated certs into the keystore:

```bash
sudo cp /etc/letsencrypt/live/<your-domain>/* /var/lib/jenkins/.ssl

cd /var/lib/jenkins/.ssl
openssl pkcs12 -export -out jenkins.p12 \
  -passout 'file:passphrase.txt' -inkey privkey.pem -in fullchain.pem

keytool -importkeystore -srckeystore jenkins.p12 \
  -srcstorepass:file passphrase.txt -srcstoretype PKCS12 \
  -destkeystore jenkins.jks -deststorepass:file passphrase.txt
# type 'yes' when prompted to overwrite the existing keystore

sudo cp jenkins.jks /etc/jenkins/jenkins.jks
sudo chown jenkins:jenkins /etc/jenkins/jenkins.jks
sudo chmod 600 /etc/jenkins/jenkins.jks

sudo systemctl daemon-reload
sudo systemctl restart jenkins
```

---

### Self-Signed Certificate

Use this approach when a public domain name is not available. Browsers will show a trust warning, but the connection will be encrypted.

All steps can be run in `/var/lib/jenkins/.ssl`. Create a passphrase file first:

```bash
sudo mkdir -p /var/lib/jenkins/.ssl
sudo chown jenkins:jenkins /var/lib/jenkins/.ssl
sudo su jenkins -s /bin/bash
cd /var/lib/jenkins/.ssl
echo my-P@ssw0rd > passphrase.txt
```

**1. Create a certificate authority:**

```bash
openssl req -x509 \
  -sha256 -days 365 \
  -nodes \
  -newkey rsa:2048 \
  -subj "/CN=<your-domain>/C=US/L=San Francisco" \
  -keyout rootCA.key -out rootCA.crt
```

**2. Create the server private key:**

```bash
openssl genrsa -out server.key 2048
```

**3. Create the CSR config (substitute your domain and IP):**

```bash
cat > csr.conf <<EOF
[ req ]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[ dn ]
C = US
ST = California
L = San Francisco
O = Fortinet
OU = CloudCSE
CN = <your-domain>

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = <your-domain>
IP.1 = <your-instance-public-ip>
EOF
```

**4. Generate the CSR:**

```bash
openssl req -new -key server.key -out server.csr -config csr.conf
```

**5. Create the SSL cert extension config:**

```bash
cat > cert.conf <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment

subjectAltName = @alt_names

[alt_names]
DNS.1 = <your-domain>
EOF
```

**6. Generate the signed certificate:**

```bash
openssl x509 -req \
  -in server.csr \
  -CA rootCA.crt -CAkey rootCA.key \
  -CAcreateserial -out server.crt \
  -days 365 \
  -sha256 -extfile cert.conf
```

**7. Convert to PKCS12, then to a Jenkins keystore:**

> Note: source and destination passwords must match, or the Jenkins service restart will fail.

```bash
openssl pkcs12 -export -out jenkins.p12 \
  -passout 'file:passphrase.txt' -inkey server.key -in server.crt

keytool -importkeystore -srckeystore jenkins.p12 \
  -srcstorepass:file passphrase.txt -srcstoretype PKCS12 \
  -destkeystore jenkins.jks -deststorepass:file passphrase.txt
```

**8. Install the keystore and configure systemd** (exit Jenkins user shell first):

```bash
sudo mkdir -p /etc/jenkins
sudo cp /var/lib/jenkins/.ssl/jenkins.jks /etc/jenkins/
sudo chown -R jenkins:jenkins /etc/jenkins
sudo chmod 700 /etc/jenkins
sudo chmod 600 /etc/jenkins/jenkins.jks

sudo mkdir -p /etc/systemd/system/jenkins.service.d
sudo cat << EOF > /etc/systemd/system/jenkins.service.d/override.conf
[Service]
Environment="JENKINS_PORT=-1"
Environment="JENKINS_HTTPS_PORT=8443"
Environment="JENKINS_HTTPS_KEYSTORE=/etc/jenkins/jenkins.jks"
Environment="JENKINS_HTTPS_KEYSTORE_PASSWORD=my-P@ssw0rd"
Environment="JENKINS_HTTPS_LISTEN_ADDRESS=0.0.0.0"
EOF
sudo systemctl daemon-reload
sudo systemctl restart jenkins
```
