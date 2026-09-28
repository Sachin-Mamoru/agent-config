---
name: terraform-review
description: >
  How to review or make changes to the infra repo's Terraform (AWS: EKS, RDS, security groups,
  IAM, S3, Lambda). Covers the manual plan/apply workflow, aws-vault profiles and their MFA
  constraint, and what to flag in a security-group or RDS-touching diff. Use when reviewing or
  writing .tf changes in infra/terraform/production, or asked to run terraform plan/apply.
---

# Terraform Review — infra repo

## Structure

`infra/terraform/production/` is a **flat** directory — no submodules under `production/` itself,
just ~50 top-level `.tf` files plus `kubernetes/`, `lambda/`, and `files/` subdirs. Files are
organized by AWS service or by product (`fdm_be.tf`, `pso_be.tf`, `udp_celery.tf`,
`metadata_extractor.tf`, `securitygroups.tf`, `iam.tf`, `rds.tf`, `s3.tf`, `eks.tf`, ...). There's
also a parallel `terraform/testing/` environment — check whether a change needs to land in both.

There is no local architecture-skill repo or separate benchmarking module for this — the repo
itself, plus `infra/README.md`, is the source of truth. Don't assume a `modules/` structure exists
unless you actually see one for the resource you're touching.

## Workflow — this is entirely manual, there is no CI automation

Confirmed: no `.yml`/`.yaml`/`Makefile` anywhere in `~/projects` calls `terraform plan` or
`terraform apply`. Per `infra/README.md`, the process is:

1. Edit the `.tf` files.
2. `terraform validate`
3. `terraform plan -out <plan-filename>` — inspect the plan
4. If it looks right, `terraform apply <plan-filename>`

**Always take extra care when:**
- The plan **deletes/recreates** a resource instead of modifying it in place
- The change touches **RDS** resources

Both of these are called out explicitly in the README — treat them as hard stop-and-confirm
points, not just "review carefully" advice.

## aws-vault profiles — same ones as `aws-vault-kubectl`, not separate

```
[profile prod-admin]
role_arn=arn:aws:iam::745847547677:role/prod-admin
source_profile=sachin-admin
mfa_serial=arn:aws:iam::736621763593:mfa/sachin-admin

[profile test-admin]
role_arn=arn:aws:iam::452998080009:role/testing-admin
source_profile=sachin-admin
mfa_serial=arn:aws:iam::736621763593:mfa/sachin-admin
```

`test-admin` → testing account (452998080009), `prod-admin` → production account (745847547677).
These are the identical profiles used for `kubectl` in the `aws-vault-kubectl` skill — there's no
terraform-specific profile.

**MFA constraint:** both profiles require MFA via `sachin-admin`'s `mfa_serial`, which needs an
interactive terminal (`/dev/tty`). `terraform plan`/`apply` will hang or fail non-interactively
unless a session is already cached from a prior interactive MFA prompt. **Concretely: you can
freely read, lint, and `terraform validate` `.tf` files, but cannot run `plan`/`apply` yourself
without Sachin first running any `aws-vault exec sachin-admin -- aws sts get-caller-identity`
(or similar) in his own terminal to cache a session.** If asked to run plan/apply and no cached
session is available, say so and ask Sachin to either cache a session or run it himself and share
the output — don't retry in a loop hoping MFA resolves itself.

## Review checklist

### Security groups (`securitygroups.tf` and similar)
- [ ] Any `cidr_blocks = ["0.0.0.0/0"]` — is this genuinely meant to be public (e.g. the LB SG's
      80/443 ingress), or should it be scoped to a specific VPC/office CIDR?
- [ ] New ingress rules — prefer `security_groups = [...]` (SG-to-SG) over `cidr_blocks` when the
      source is another resource in the same VPC, not an external network
- [ ] Egress `protocol = "ALL"` / `"-1"` with `0.0.0.0/0` — expected for node/lambda egress via NAT,
      but flag if added to something that shouldn't need broad outbound
- [ ] RDS ingress — is the new CIDR/SG actually necessary, or could it use an existing rule? The
      repo already carries one intentionally-temporary rule (dev→prod RDS, commented as removable
      "once the dust settles") — don't add more temporary exceptions without a similar comment
      explaining why and that it should eventually be removed
- [ ] Rule `description` set — most existing rules have one; new rules without a description are
      harder for the next reviewer to justify

### General plan review
- [ ] Does the plan show any `-/+` (destroy and recreate)? If yes, stop — confirm this is expected
      and understand the downtime/data-loss implications before applying
- [ ] Does the plan touch `aws_db_instance`, `aws_rds_cluster`, or anything under `rds.tf`? If yes,
      treat as high-risk per README — get a second look before applying
- [ ] Check whether the same logical change is needed in both `terraform/production/` and
      `terraform/testing/` (parallel environments) — a fix in only one is a common gap
- [ ] `terraform validate` passed, and `.terraform.lock.hcl` isn't being hand-edited

## What this skill does NOT cover

Module-level design decisions (e.g. "should this be its own module") — that's
`architecture-best-practices`, specifically `references/aws-k8s-infra.md`. This skill is about
reviewing/writing the diff correctly and safely, not about infra architecture from scratch.
