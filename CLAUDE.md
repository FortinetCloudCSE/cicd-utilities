# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

CI/CD infrastructure-as-code toolkit for the FortinetCloudCSE team. Automates GitHub repo creation, Jenkins pipeline setup, AWS infrastructure provisioning, and GitHub status alerting.

## Repository Structure

| Directory | Purpose |
|---|---|
| `jenkins/` | Shell scripts to create/modify/delete GitHub repos and Jenkins pipelines |
| `launch-templates/` | CloudFormation for scalable Jenkins cluster (main node + auto-scaling workers) |
| `GHA/` | CloudFormation for GitHub Actions self-hosted EC2 runner |
| `ecs-stack/` | CloudFormation for ECS container application deployments |
| `status-check-lambda/` | Lambda + CloudFormation for GitHub webhook → SNS failure alerts |

See `launch-templates/CLAUDE.md` for detailed guidance on that subsystem.

## Common Commands

### Validate CloudFormation templates
```bash
cfn-lint <template>.yaml
```

### Jenkins scripts (run from `jenkins/`)
```bash
# Create new GitHub repo + Jenkins pipeline
./setup-cicd.sh [-t template_repo] [-r] [-b] [-s] [-j userid] [-f config.xml] [-c collab...] <repo_name>

# Modify existing repo (add collaborators, webhooks, branch protections, pipeline)
./modify-cicd.sh [-j userid] [-c collab...] [-w] [-r] [-u] [-b] [-f config.xml] [-a] <repo_name>

# Batch run modify-cicd.sh on a list of repos
./modify-cicd-runner.sh <repos.txt> [modify-cicd flags...]

# Delete GitHub repo + Jenkins pipeline
./delete-cicd.sh <jenkins_userid> <repo_name>

# Make programmatic commits to a repo via GitHub API (edit files, copy from other repos, add submodules)
# Edit the script's code block to add desired operations before running
./edit-commit.sh <repo_name>

# Get GitHub custom properties (cloud-provider, function) for a repo
./get-custom-properties.sh -t <repo_name>
```

### Deploy CloudFormation stacks
```bash
# Jenkins cluster (multi-node with auto-scaling workers)
aws cloudformation create-stack --stack-name jenkins-cluster \
  --template-body file://launch-templates/jenkins-cluster.yaml \
  --parameters file://launch-templates/jenkins-params.json \
  --capabilities CAPABILITY_NAMED_IAM

# Jenkins single EC2 (simpler alternative to the cluster)
aws cloudformation create-stack --stack-name jenkins-single \
  --template-body file://jenkins/launch-jenkins-ec2.yml \
  --capabilities CAPABILITY_NAMED_IAM

# GHA self-hosted runner
aws cloudformation create-stack --stack-name gha-runner \
  --template-body file://GHA/launch-runner-ec2.yml \
  --parameters file://GHA/launch-runner-params.json \
  --capabilities CAPABILITY_NAMED_IAM

# ECS app stack (ecs-app-template.yml is not tracked in this repo; obtain separately)
aws cloudformation create-stack --stack-name <stack-name> \
  --template-body file://ecs-stack/ecs-app-template.yml \
  --parameters file://ecs-stack/ecs-app-params.json \
  --capabilities CAPABILITY_NAMED_IAM
```

### Status check Lambda
```bash
# Package and deploy
cd status-check-lambda
zip status-check-email.zip status-check-email.py
aws s3 cp status-check-email.zip s3://<bucket>/<key>
aws cloudformation deploy --stack-name status-check-alerts \
  --template-file status-check-stack.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LambdaCodeS3Bucket=<bucket> LambdaCodeS3Key=<key> \
    WebhookSecret="<secret>" SnsTopicName=status-check-alerts
```

## Architecture Overview

### Jenkins Scripts Flow
`setup-cicd.sh` and `modify-cicd.sh` depend on local files that must exist before running:
- `~/.jenkins-cli` — Jenkins personal access token
- `~/jenkins-cli.jar` — Jenkins CLI jar
- `gh` CLI authenticated to GitHub

`setup-cicd.sh` orchestrates: create repo → enable Pages → branch protections → add collaborators → create Jenkins job (via `jenkins-cli.jar` + `template-config.xml`) → set GitHub webhook → trigger initial build.

`template-config.xml` is the Jenkins pipeline template. `jenkins/config.xml` is the active pipeline config (reads `Jenkinsfile` from the repo).

`edit-commit.sh` uses the GitHub Git Trees API to commit multiple file changes atomically without a local clone. It provides three helper functions to build the commit: `update_tree_array_sed` (find/replace in existing file), `update_tree_array_new_file` (copy file from another FortinetCloudCSE repo), and `add_submodule`.

### Jenkins Cluster (launch-templates/)
- **Main node** (m4.large): Jenkins server on ports 8080/8443, controls workers via EC2 Fleet plugin
- **Worker nodes** (m4.xlarge, ASG min=0/max=3/desired=0): Scale to zero when idle; have Terraform, cfn-lint, tflint, Docker, Python 3 pre-installed
- IAM role grants S3 (backup/restore), EC2 Fleet, and SSM Session Manager permissions
- HTTPS via self-signed keystore stored in S3; migration from existing Jenkins via S3 backup of `JENKINS_HOME`

### GHA Runner (GHA/)
EC2-based self-hosted runner registered to a specific GitHub repo. **GHA registration tokens expire after 60 minutes**—generate the token just before deploying the stack or store it in SSM Parameter Store and fetch it at launch time.

### Status Check Lambda
Receives GitHub `check_run` and `status` webhooks, validates HMAC-SHA256 signature, filters for `ci/jenkins/build-status` failures, and publishes to SNS. Exposed via a Lambda Function URL (no API Gateway). Environment variables: `SNS_TOPIC_ARN`, `WEBHOOK_SECRET`.

## Gitignored Sensitive Files
Parameter files with real values (`*-params.json` without `-template`) and secrets (`jenkins-cli`, etc.) are gitignored. Always copy the `*-template.json` files and populate locally.
