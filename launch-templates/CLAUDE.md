# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

AWS CloudFormation templates for deploying a scalable Jenkins CI/CD cluster on EC2 instances. Supports both fresh installations and migration from existing Jenkins setups.

## Key Files

- `jenkins-cluster.yaml` — The CloudFormation template defining all AWS resources
- `jenkins-params-template.json` — Parameter template (copy to `jenkins-params.json` and populate before deploying)
- `jenkins-params.json` — User-populated deployment parameters (gitignored or left blank in repo)
- `README.md` — Step-by-step deployment and configuration guide

## Deployment Commands

```bash
# Copy and populate parameters
cp jenkins-params-template.json jenkins-params.json

# Deploy CloudFormation stack
aws cloudformation create-stack --stack-name jenkins-cluster \
  --template-body file://./jenkins-cluster.yaml \
  --parameters file://./jenkins-params.json --capabilities CAPABILITY_NAMED_IAM
```

## Template Validation

Use cfn-lint (installed on Jenkins worker nodes) to validate the template before deployment:

```bash
cfn-lint jenkins-cluster.yaml
```

## Architecture

The template creates two EC2 launch templates and supporting infrastructure:

**Main Node** (`JenkinsMainLaunchTemplate`, m4.large, 16GB):
- Runs Jenkins server (Java 17, Docker)
- Accessible on ports 8080 (HTTP) and 8443 (HTTPS)
- Controls worker nodes via the EC2 Fleet plugin

**Worker Nodes** (`JenkinsWorkerLaunchTemplate`, m4.xlarge, 8GB):
- Pre-installed with: Terraform, cfn-lint, tflint, Docker, Python 3, jq, Git
- Managed by Auto Scaling Group (`JenkinsASG`, min=0, max=3, desired=0)
- Spun up on demand by the main node via the EC2 Fleet Jenkins plugin

**IAM Role** grants:
- S3 read/write (for JENKINS_HOME backup/restore migration)
- EC2 Fleet plugin permissions (describe instances, modify, terminate)
- SSM Session Manager access (no SSH bastion needed)

## CloudFormation Parameters

| Parameter | Description |
|---|---|
| `MNKeyPair` | Main node EC2 key pair name |
| `WNKeyPair` | Worker node EC2 key pair name |
| `VPCId` | VPC ID for deployment |
| `MySubnet` | Subnet ID for deployment |
| `JenkinsBucket` | S3 bucket ARN (migration only) |
| `JenkinsHomeS3Location` | S3 URI of JENKINS_HOME backup (migration only) |
| `JenkinsKeyStoreLocation` | S3 URI of Jenkins HTTPS keystore (migration only) |

For a fresh install, leave the three Jenkins-specific parameters as empty strings `""`.

## Migration Scenario

When migrating an existing Jenkins installation: upload the existing `JENKINS_HOME` directory and HTTPS keystore to S3, then populate all seven parameters. The main node UserData will automatically restore from S3 on launch.
