## Getting Started

These AWS launch templates can help you get started setting up a basic Jenkins cluster on a set of EC2 instances.

The first set of steps are for creating a new cluster from scratch, and the second are for the scenario where you've uploaded the JENKINS_HOME
directory and keystore of an existing Jenkins installation to an S3 location and want to migrate to a new cluster.  

### Starting from Scratch

First, you'll need to populate the parameters file with references to your existing AWS resources. Then you can go ahead and deploy the launch template. For this scenario where we're creating a new cluster from scratch, leave the three Jenkins parameter values blank ("").

| Parameter                | Description                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------------- |               
| MNKeyPair                | Main node key pair.                                                                      |
| WNKeyPair                | Worker node key pair.                                                                    |
| VPCId                    | ID of VPC where cluster will be deployed.                                                |
| MySubnet                 | ID of subnet where cluster will be deployed.                                             | 
| JenkinsBucket            | ARN of S3 bucket containing existing JENKINS_HOME directory and keystore. (if migrating) | 
| JenkinsHomeS3Location    | S3 URI of JENKINS_HOME                                                                   |
| JenkinsKeyStoreLocation  | S3 URI of location of Jenkins keystore                                                   |


```
cp jenkins-params-template.json jenkins-params.json 

# Paste in parameter values to jenkins-params.json 

aws cloudformation create-stack --stack-name jenkins-cluster \
  --template-body file://./jenkins-cluster.yaml \
  --parameters file://./jenkins-params.json --capabilities CAPABILITY_NAMED_IAM
```
After successful launch of the CloudFormation stack, launch an EC2 instance from the created launch template with the name that starts with "JenkinsMainLaunchTemplate..."

Access the instance via session manager and retrieve the initial Jenkins password:

```
> sudo cat /var/lib/jenkins/secrets/initialAdminPassword
abcd1234efghijkl09876plmokn654322
```
Then, retrieve the EC2 instance public IP, open up a browser, and navigate to http://<public IP>:8080.

The Jenkins console will open and will ask you for the password. Paste it into the text box. Then, choose to either install a specific set of plugins or accept the default installation. Once plugin installation is finished, you may create a default user with which to access the console or skip for now. If you skip, you'll need to keep the initial password handy and use that to access the console.

The main node of your cluster is now ready to be configured.

### HTTPS Setup

See **[docs/https-setup.md](docs/https-setup.md)** for full instructions, including:
- Let's Encrypt certificate setup (recommended for instances with a public domain)
- Certificate renewal
- Self-signed certificate setup (for internal or testing use)

### Migrating to a new Jenkins Installation

To utilize these templates to migrate an existing Jenkins installation to a new server, copy objects within the existing JENKINS_HOME and JENKINS_HTTPS_KEYSTORE locations to an S3 location and specify the S3 URI of each in the CloudFormation parameter template file as values for the JenkinsHomeS3Location and JenkinsKeyStoreLocation parameters, respectively. In order for the EC2 instance where your Jenkins Main node will be deployed to have permissions to download those objects from S3, ensure you also paste in the ARN of the bucket where these objects are located as a value for the JenkinsBucket parameter as well.

Once you do launch the "JenkinsMainLaunchTemplate..." and it deploys successfully, your new Jenkins install will be ready to go and you can navigate to the public IP of the EC2 instance on port 8080 to access Jenkins.

Update the Route 53 record for your Jenkins domain to point to the public IP of the new instance.

If you'd like to enable https for the server, you'll need to access the ssm-user command line of the EC2 instance via session manager and update the Jenkins systemd service settings. The launch template user data is configured to copy the JENKINS_HTTPS_KEYSTORE from S3 to /etc/jenkins, so we're specifying that as the new keystore location here in this example as well. This method also assumes your new domain name matches the old one which the keystore is configured for.

```
sudo mkdir -p /etc/systemd/system/jenkins.service.d
sudo touch /etc/systemd/system/jenkins.service.d/override.conf
sudo cat << EOF > /etc/systemd/system/jenkins.service.d/override.conf
[Service]
Environment="JENKINS_PORT=-1"
Environment="JENKINS_HTTPS_PORT=8443"
Environment="JENKINS_HTTPS_KEYSTORE=/etc/jenkins/jenkins.jks"
Environment="JENKINS_HTTPS_KEYSTORE_PASSWORD=<Jenkins keystore password>"
Environment="JENKINS_HTTPS_LISTEN_ADDRESS=0.0.0.0"
EOF
sudo systemctl daemon-reload
sudo systemctl restart jenkins
```

### Configuring EC2 Fleet Plugin

The Jenkins [EC2 Fleet plugin](https://plugins.jenkins.io/ec2-fleet/) enables integration with an Auto Scaling group in AWS for the cases when worker node scaling is needed and/or a node is having issues and needs to be shut down and replaced. 

To configure the plugin, you'll first need to add the private key of your worker node AWS key pair to the Jenkins console. 

In Jenkins, navigate to Dashboard > Manage Jenkins > Credentials. Under **Stores scoped to Jenkins**, under the **Domains** heading, click **(global)**.

!["creds-global"](creds-global.png)

Click **Add Credentials**

!["add-creds"](add-creds.png)

Select **SSH Username with private key** in the **Kind** dropdown. Leave **Scope** set to Global, and choose an ID for the credential. Optionally enter a description. For **Username**, paste in the name of the key pair you specified for the worker node launch template during setup.

Under **Private Key**, click **Enter Directly**, and then click **Add**. Paste in the key, and click **Create**.

!["key-pair-enter"](key-pair-enter.png)

Now, in Jenkins, navigate to Dashboard > Manage Jenkins > Clouds, and select **New Cloud**.

!["new-cloud"](new-cloud.png)

Give the cloud a name, select type **Amazon EC2 Fleet**, and click **Create**.

!["new-cloud-2"](new-cloud-2.png)

On the following screen, select the region where your Auto Scaling group exists, leave **AWS Credentials** set to none, and leave **Endpoint** blank.

!["new-cloud-specs-1"](new-cloud-specs-1.png)

Under **EC2 Fleet**, select the Auto Scaling group created at setup ("JenkinsASG" if you haven't altered the CloudFormation template). Under **Launcher**, select **Launch agents via SSH**. Under credentials, select the credential created above. Select **Non verifying Verification Strategy** for **Host Key Verification Strategy**. 

!["new-cloud-specs-2"](new-cloud-specs-2.png)

Under **Advanced**, ensure Port is set to **22**, and leave all other settings as is, except for the following:

|                                  |     |
| -------------------------------- | --- |
| Connection Timeout in Seconds:   | 300 |
| Maximum Number of Retries:       | 10  |
| Seconds to Wait Between Retries: | 15  |

Ensure the **Use TCP_NODELAY flag on the SSH connection** and **Private IP** boxes are checked. Click **Save**.

!["new-cloud-specs-3"](new-cloud-specs-3.png)

Also set the following under the main cloud configuration:

|                                          |     |
| ---------------------------------------- | --- |
| Maximum Init Connection Timeout in sec:  | 300 |
| Cloud Status Interval in sec:            | 10  |

You should now see a new instance creating in the AWS EC2 console.

In Jenkins, you can also navigate to Dashboard > Manage Jenkins > Nodes, and you'll see the new node there with a name in the form of '\<cloud\> \<EC2 instance id\>'. It may take a few moments to become available.

### Integrating GitHub

See **[docs/github-integration.md](docs/github-integration.md)** for full instructions, including:
- GitHub PAT (Personal Access Token) setup for build status checks
- Private repository deploy key setup

---

## Further Reading

| Guide | Contents |
| --- | --- |
| [docs/https-setup.md](docs/https-setup.md) | Let's Encrypt new cert, cert renewal, self-signed cert alternative |
| [docs/github-integration.md](docs/github-integration.md) | GitHub PAT for status checks, private repo deploy keys |
| [docs/operations.md](docs/operations.md) | Jenkins upgrade procedure, git workspace troubleshooting |
