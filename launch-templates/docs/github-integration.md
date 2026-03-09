## GitHub Integration

---

### GitHub PAT for Status Checks

A GitHub Personal Access Token (classic) is required for Jenkins to send build status checks back to GitHub and interact with webhooks.

> **Important:** When a PAT expires it must be **recreated** in GitHub, not just regenerated. Regenerating an expired token appears to work but the connection will fail. Delete the old credential in Jenkins and create a new one with the new token.

**Required GitHub permissions:** `repo` (all), `admin:repo_hook` (all)

**Creating the PAT in GitHub:**

1. Go to GitHub > profile icon > **Settings** > **Developer settings** > **Personal access tokens** > **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Select the `repo` and `admin:repo_hook` permission scopes
4. Click **Generate token** and copy the value immediately

**Adding the PAT to Jenkins:**

1. Navigate to **Manage Jenkins** > **System** > **GitHub** > **GitHub Servers**
2. Under **Credentials**, click **+ Add** and select **Jenkins**
3. Set **Kind** to **Secret text**, paste the PAT in the **Secret** field, and give it an **ID** (use the same name as the GitHub PAT for traceability)
4. Select the new credential from the dropdown and click **Test connection** to verify

**If the token still doesn't work after recreating:**

Delete the credential in Jenkins completely, then go to **System** > **GitHub** > **GitHub Servers** and re-add it fresh by clicking **Add** (Kind: Secret text). Click **Save** at the bottom of the page after adding.

---

### Private Repository Deploy Key

Use a deploy key when a Jenkins job needs to access a private GitHub repository via SSH (e.g. for webhook-triggered pipelines).

**1. Generate the key pair** (run locally or on the Jenkins main node):

```bash
ssh-keygen -t ed25519 -C "jenkins-deploy-key-<repo-name>" -f jenkins_deploy_key_<repo-name>
```

This produces a private key (`jenkins_deploy_key_<repo-name>`) and public key (`jenkins_deploy_key_<repo-name>.pub`).

**2. Add the private key as a Jenkins credential:**

In Jenkins, navigate to **Manage Jenkins** > **Credentials** > **(global)** > **Add Credentials**.

- **Kind:** SSH Username with Private Key
- **Username:** `FortinetCloudCSETeam`
- **Private Key:** Enter directly — paste the full contents of the private key file, including the `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----` lines

**3. Update the pipeline job to use SSH:**

In the job configuration, go to **Pipeline** > **Definition** > **Pipeline script from SCM** > **SCM** > **Repositories** > **Repository URL** and change the URL to the repo's SSH format:

```
git@github.com:FortinetCloudCSE/<repo-name>.git
```

Select the credential created above under **Credentials**.

**4. Add the public key to GitHub:**

In the GitHub repository, go to **Settings** > **Deploy keys** > **Add deploy key**. Paste the contents of the `.pub` file and save.
