## Operations

---

### Upgrading Jenkins

1. Access the Jenkins main node via Session Manager.

2. Confirm the location of `jenkins.war`:

```bash
sudo systemctl status jenkins
# Look for the '-jar' argument under CGroup — that path is where the .war lives
```

3. Download the target version:

```bash
wget https://updates.jenkins.io/download/war/<version>/jenkins.war
```

4. Set ownership and move to the location found above:

```bash
sudo chown root:root jenkins.war
sudo mv jenkins.war /usr/share/java/jenkins.war
```

5. Restart Jenkins:

```bash
sudo systemctl daemon-reload
sudo systemctl restart jenkins
```

---

### Git / Workspace Troubleshooting

**Workspace locations:**

| Node | Path |
|---|---|
| Main node | `/var/lib/jenkins/workspace` |
| Worker node | `/tmp/jenkins-<hash>/workspace` |

**Corrupted workspace:**

If a build fails with a git error that suggests a corrupted or inconsistent workspace state, delete the workspace directory on the worker node and re-run the build:

```bash
rm -rf /tmp/jenkins-<hash>/workspace/<job-name>
```

The workspace will be recloned fresh on the next run.
