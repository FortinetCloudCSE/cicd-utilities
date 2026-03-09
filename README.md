# cicd-utilities

A monorepo of CI/CD infrastructure-as-code and automation scripts for the FortinetCloudCSE team. It covers two main areas: **GitHub/Jenkins repo management scripts** and **AWS infrastructure templates** for running CI/CD workloads.

---

## Modules

### `jenkins/` — GitHub Repo & Jenkins Pipeline Automation

Shell scripts for day-to-day management of FortinetCloudCSE GitHub repos and their associated Jenkins pipelines.

**Note: Many of the functionalities in these scripts have been migrated into the gh-jenkins-cli tool found at https://github.com/robreris/gh-jenkins-cli**

| Script | Purpose |
|---|---|
| `setup-cicd.sh` | Create a new GitHub repo and (optionally) a Jenkins pipeline. Orchestrates repo creation, GitHub Pages, branch protections, collaborator access, and an initial build trigger. |
| `modify-cicd.sh` | Modify an existing repo — add collaborators, webhooks, branch protections, or a Jenkins pipeline. |
| `modify-cicd-runner.sh` | Batch wrapper: runs `modify-cicd.sh` over a list of repo names from a text file. |
| `delete-cicd.sh` | Delete a GitHub repo and its Jenkins pipeline. |
| `edit-commit.sh` | Make programmatic commits to a repo via the GitHub Git Trees API without a local clone. Supports in-place file edits (sed-style), copying files from other FortinetCloudCSE repos, and adding submodules. Edit the script's code block to define the desired operations before running. |
| `get-custom-properties.sh` | Retrieve GitHub custom properties (`cloud-provider`, `function`) for a given repo. |

**Prerequisites:** `~/jenkins-cli.jar`, `~/.jenkins-cli` (PAT), and `gh` CLI authenticated to GitHub.

`template-config.xml` is the Jenkins pipeline job template used when creating new pipelines. `config.xml` is the active pipeline config that reads a `Jenkinsfile` from the target repo. `launch-jenkins-ec2.yml` is a standalone CloudFormation template for a simple single-EC2 Jenkins server (see `launch-templates/` for the full auto-scaling cluster).

---

### `launch-templates/` — Jenkins Cluster on EC2 (CloudFormation)

A CloudFormation template (`jenkins-cluster.yaml`) that provisions a scalable Jenkins cluster:

- **Main node** (m4.large): Runs the Jenkins server on ports 8080/8443. HTTPS uses a self-signed keystore stored in S3.
- **Worker nodes** (m4.xlarge): Managed by an Auto Scaling Group (min=0, max=3, desired=0) — scale to zero when idle, spun up on demand by the EC2 Fleet Jenkins plugin. Come pre-installed with Terraform, cfn-lint, tflint, Docker, Python 3, jq, and Git.
- **IAM role**: Grants S3 read/write (for `JENKINS_HOME` backup/restore), EC2 Fleet plugin permissions, and SSM Session Manager access (no SSH bastion needed).

Supports both fresh installs and migration from an existing Jenkins instance by restoring a `JENKINS_HOME` backup from S3.

Copy `jenkins-params-template.json` → `jenkins-params.json` and populate before deploying. See `launch-templates/README.md` for full parameter details.

---

### `GHA/` — GitHub Actions Self-Hosted Runner on EC2 (CloudFormation)

A CloudFormation template (`launch-runner-ec2.yml`) that launches a single EC2 instance registered as a self-hosted GitHub Actions runner for a specific repo.

Key parameters: `OrgName`, `RepoName`, `GHAToken` (registration token — **expires after 60 minutes**, so generate it just before deploying or fetch it just-in-time from SSM Parameter Store), `RunnerVersion`, `HashCheck` (SHA-256 of the runner binary for integrity verification), `InstanceType`, and networking parameters.

Copy `launch-runner-params-template.json` → `launch-runner-params.json` and populate before deploying. See `GHA/README.md` for the full setup walkthrough.

---

### `ecs-stack/` — ECS Container App Deployment (CloudFormation)

CloudFormation parameters (`ecs-app-params-template.json`) for deploying a containerized web application to an ECS cluster. The stack provisions an ECS cluster fronted by an Elastic IP, and is configured to automatically redeploy when a new image is pushed to the associated ECR repository.

Key parameters: `ECRRepo`, `ECRRepoName`, `AppVPC`, `AppSubnet`, `ElasticIPAlloc`, `AllowedCidr`, `KeyPair`.

Copy `ecs-app-params-template.json` → `ecs-app-params.json` and populate before deploying. See `ecs-stack/README.md` for the full ECR build/push workflow.

---

### `status-check-lambda/` — GitHub Webhook → SNS Failure Alerts

A Python Lambda function (`status-check-email.py`) and CloudFormation stack (`status-check-stack.yaml`) that receives GitHub `check_run` and `status` webhooks, validates the HMAC-SHA256 signature, filters for `ci/jenkins/build-status` failures, and publishes a notification to an SNS topic.

The Lambda is exposed via a **Lambda Function URL** (no API Gateway required). Required environment variables: `SNS_TOPIC_ARN` and `WEBHOOK_SECRET`.

Deploy by zipping the Python file, uploading to S3, then running `aws cloudformation deploy` with the S3 location and webhook secret as parameter overrides.

---

## TODO / Known Gaps

- **`ecs-stack/ecs-app-template.yml` is missing** — the `ecs-stack/` directory contains parameter files and a README that reference this CloudFormation template, but the template itself is not present in the repository. It needs to be added.
- **`jenkins/launch-jenkins-ec2.yml`** — a standalone single-EC2 Jenkins CloudFormation template exists in `jenkins/` but has no accompanying README or parameter template file.
- **`edit-commit.sh` is a template script** — the operations it performs are defined by editing the script's code block directly before each run. There is no CLI interface for specifying operations; the script is intended to be modified and re-run as needed.
