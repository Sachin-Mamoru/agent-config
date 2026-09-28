# AWS & Kubernetes/EKS Infrastructure Architecture

## Cluster architecture (EKS)
- **Node group strategy**: separate node groups by workload shape, not just one generic pool. Common split: general-purpose services, memory-optimized (for anything caching/in-memory heavy), and spot-instance node groups for fault-tolerant/batch workloads (Celery workers are a great spot-instance fit if tasks are idempotent and retryable — see python-fastapi.md).
- **Namespace strategy**: namespaces should map to a real isolation boundary (team, environment, or bounded context) — not be created ad hoc. Use `ResourceQuota` and `LimitRange` per namespace so one team's runaway workload can't starve the cluster (bulkhead pattern again, at the infra layer).
- **Multi-AZ by default**: spread nodes and pods across availability zones (`topologySpreadConstraints` or pod anti-affinity) so a single AZ failure doesn't take down all replicas of a service.

## Autoscaling — pick the right signal
| Mechanism | Scales | Signal | Best fit |
|---|---|---|---|
| HPA (Horizontal Pod Autoscaler) | Pod replica count | CPU/memory, or custom metrics | Standard request-driven services with a fairly linear CPU-to-load relationship |
| KEDA | Pod replica count (incl. scale-to-zero) | External event source (queue depth, Kafka lag, cron schedule, custom metrics) | Celery/RabbitMQ workers, anything event/queue-driven where CPU isn't a good proxy for backlog |
| Cluster Autoscaler / Karpenter | Node count | Unschedulable pods | Underlying capacity — needs to work in concert with HPA/KEDA, not instead of them |
| VPA (Vertical Pod Autoscaler) | Per-pod resource requests/limits | Historical usage | Right-sizing requests/limits, usually run in recommendation-only mode alongside HPA rather than combined live (the two can fight each other) |

Common mistake: relying on HPA/CPU-based scaling for queue-consumer workloads (Celery workers). CPU can look low even with a large backlog if tasks are I/O-bound (waiting on a downstream API or DB), so the autoscaler under-provisions exactly when it's needed most. KEDA scaling on RabbitMQ queue depth is the correct signal for this shape of workload.

## Ephemeral storage & resource sizing
- Set explicit `requests` and `limits` for CPU, memory, and ephemeral storage on every pod — an unset ephemeral-storage limit means a single pod filling up local disk (logs, temp files, large task payloads) can evict other pods on the same node.
- Size `requests` close to real steady-state usage (informed by VPA recommendations or observed metrics) rather than guessing high "to be safe" — over-requesting wastes cluster capacity and inflates cost without improving reliability; under-requesting risks OOMKills. This is a genuinely empirical decision, not a one-time guess — revisit as observed usage data (Dynatrace/Logfire) accumulates.

## Networking & IAM
- **IRSA (IAM Roles for Service Accounts)**: give pods AWS permissions via a scoped IAM role bound to a Kubernetes ServiceAccount, not by injecting long-lived AWS credentials as secrets. Scope each role to least privilege per workload, not one shared role across the cluster.
- **Cross-namespace ServiceAccount risk**: a ServiceAccount's token is a bearer credential within its RBAC scope — audit that ServiceAccounts aren't granted broader RBAC permissions (e.g., cluster-wide) than the workload actually needs. This is a common source of privilege-escalation risk in multi-tenant clusters.
- **Network policies**: default-deny between namespaces, explicit allow rules for actual required traffic — don't rely on namespace isolation alone, since by default all pods can reach all pods across namespaces on a flat cluster network.

## Observability architecture
- **Three pillars, not just one**: metrics (aggregate health/trends), logs (what happened, structured not just plain text), traces (how a single request flowed across services). Dynatrace-style APM platforms typically cover all three, but architecturally the important discipline is: every service emits structured logs with a correlation/trace ID, and every cross-service call propagates that ID.
- **Dashboards should answer specific on-call questions**, not just display everything available. A good dashboard-design test: "if a specific alert fires at 3am, does this dashboard help someone diagnose it in under 2 minutes?" If not, it's a data dump, not a diagnostic tool.
- **Alert on symptoms, not causes** where possible (e.g., alert on elevated error rate or latency SLO breach, not on "CPU is at 80%" which may be perfectly healthy). Cause-based alerts create noise; symptom-based alerts (paired with cause-based dashboards for diagnosis after the alert fires) reduce alert fatigue.

## Cost optimization (a real architectural concern, not just a finance one)
- Spot instances for fault-tolerant, retryable workloads (Celery workers, batch jobs, CI runners) — can cut compute cost significantly, but only safe if the workload is genuinely tolerant of sudden termination (which ties back to idempotent task design).
- Right-sizing via VPA recommendations rather than static overprovisioning.
- Savings Plans / Reserved Instances for genuinely steady-state baseline load, spot/on-demand for the variable portion above baseline.

## CI/CD architecture
- Build once, promote the same artifact through environments (dev → staging → prod) rather than rebuilding per environment — eliminates "worked in staging, broke in prod because of a different build" class of bugs.
- Progressive delivery (canary or blue/green) for anything with meaningful blast radius, with automated rollback triggered by the same symptom-based alerts used for on-call (see observability above) — this operationalizes Nygard's "design for failure" principle at the deployment layer, not just the code layer.
