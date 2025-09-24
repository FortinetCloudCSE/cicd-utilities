# Status Check Alert Lambda

This Lambda receives GitHub webhook events, validates the signature, and publishes an SNS notification whenever the `ci/jenkins/build-status` check fails.

## What the Stack Deploys

The CloudFormation template (`status-check-stack.yaml`) provisions:
- An SNS topic that fanouts failure notifications.
- An IAM execution role with permission to publish to the topic and write function logs.
- The Lambda function that validates the webhook signature and pushes alerts to SNS.
- A Lambda Function URL (public HTTPS endpoint) you register as the GitHub webhook target.
- An optional CloudWatch Logs retention policy (default 14 days).

## Prepare the Deployment Package

1. Ensure the repo contains the current `status-check-email.py` file.
2. Package the Lambda handler into a zip file:
   ```bash
   zip status-check-email.zip status-check-email.py
   ```
3. Upload the zip to an S3 bucket in the target AWS account/region:
   ```bash
   aws s3 cp status-check-email.zip s3://my-artifacts-bucket/status-check/status-check-email.zip
   ```

Record the bucket name and key; you will pass them to CloudFormation.

## Generate the Webhook Secret

Create a random secret that both GitHub and the Lambda will share:
```bash
openssl rand -base64 32
```
You’ll use this string twice—once when deploying the stack and once when configuring the GitHub webhook.

## Deploy with CloudFormation

Use the AWS CLI (or Console) to deploy `status-check-stack.yaml`. Example CLI command:
```bash
aws cloudformation deploy   --stack-name status-check-alerts   --template-file status-check-stack.yaml   --capabilities CAPABILITY_IAM   --parameter-overrides       LambdaCodeS3Bucket=my-artifacts-bucket       LambdaCodeS3Key=status-check/status-check-email.zip       WebhookSecret="<paste-generated-secret>"       SnsTopicName=status-check-alerts       LogRetentionDays=14
```

After the stack finishes, note the outputs:
- `StatusCheckFunctionUrl` – public HTTPS endpoint for GitHub webhooks.
- `StatusCheckTopicArn` – SNS topic ARN (subscribe email/SMS/ChatOps endpoints as needed).

## Configure GitHub Webhook

1. In GitHub navigate to **Settings → Webhooks** at the org or repo level.
2. Add a new webhook:
   - **Payload URL**: `StatusCheckFunctionUrl` from the stack outputs.
   - **Content type**: `application/json`.
   - **Secret**: the same value supplied to the CloudFormation parameter.
   - Select the `check_run` and `status` events (or “Send me everything” if preferred).

GitHub will send a test delivery; the Lambda responds `200` if the signature matches.

## Subscribing to Alerts

- For email/SMS/ChatOps, create subscriptions on the SNS topic (Console or CLI). Example email subscription:
  ```bash
  aws sns subscribe     --topic-arn <StatusCheckTopicArn>     --protocol email     --notification-endpoint alerts@example.com
  ```
  Confirm the subscription from the email message to start receiving alerts.

## Updating the Function

To deploy code updates:
1. Re-package the handler zip and upload it to S3 (overwriting or using a new key).
2. Redeploy the stack with `aws cloudformation deploy` using the updated key.

## Rotating the Webhook Secret

1. Generate a fresh secret.
2. Update the CloudFormation stack with the new `WebhookSecret` parameter.
3. Immediately update the GitHub webhook configuration with the same secret.

## Tearing Down

Remove the stack when no longer needed:
```bash
aws cloudformation delete-stack --stack-name status-check-alerts
```
This deletes the Lambda, function URL, IAM role, log group, and SNS topic (ensure subscribers are notified beforehand).
