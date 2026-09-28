---
name: k8s-debug
description: 'Standard procedure for debugging Kubernetes pod failures (CrashLoopBackOff, OOMKilled, ImagePullBackOff, Init failures, etc.). Use when a pod is not running or restarting repeatedly.'
---

# Kubernetes Pod Debugging

## Step 1 — Identify the failing pod

```bash
aws-vault exec <env>-admin -- kubectl get pods -n <namespace>
```

Sort by age (newest first):
```bash
aws-vault exec <env>-admin -- kubectl get pods -n <namespace> --sort-by=.metadata.creationTimestamp | tac
```

## Step 2 — Get the root cause from logs

```bash
# Logs from previous (crashed) container
aws-vault exec <env>-admin -- kubectl logs -n <namespace> <pod-name> --previous 2>&1 | head -80

# If head doesn't show the error, grep for it
aws-vault exec <env>-admin -- kubectl logs -n <namespace> <pod-name> --previous 2>&1 | grep -E "ERROR|Exception|Error|FATAL" | head -20
```

## Step 3 — Get pod details for non-log failures

```bash
aws-vault exec <env>-admin -- kubectl describe pod -n <namespace> <pod-name>
```

Look for: `Events` section at the bottom, `State`, `Last State`, `Reason`.

## Common Failure Patterns

| Status | Likely cause | Where to look |
|--------|-------------|---------------|
| `CrashLoopBackOff` | App crash on startup | `kubectl logs --previous` |
| `OOMKilled` | Memory limit exceeded | `kubectl describe` → Last State reason |
| `ImagePullBackOff` | Image doesn't exist in ECR | `kubectl describe` → Events |
| `Init:0/N` | Init container waiting/failing | `kubectl logs -c <init-container-name>` |
| `CreateContainerConfigError` | Missing configmap key (non-optional) | `kubectl describe` → Events |

## Init container logs

```bash
aws-vault exec <env>-admin -- kubectl logs -n <namespace> <pod-name> -c <init-container-name>
```

## Namespace Reference

| Environment | Namespace |
|-------------|-----------|
| development | `test-development` |
| staging | `test-staging-v2` |
| acceptance lilly | `client-lilly-acceptance` |
| acceptance playground | `client-playground-acceptance` |

## After identifying root cause

- **Missing env var**: fix in the kustomize overlay or base deployment — see `kustomize-deploy` skill
- **Missing configmap key**: add to the overlay's `configmap-env.yaml`
- **Wrong image**: re-trigger deployment with correct commit hash
- **OOM**: increase memory limits in the overlay's `deployment.yaml`
