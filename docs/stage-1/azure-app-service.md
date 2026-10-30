# Node package deployment to Azure App Service

Stage 1 deploys the sample [simple_web_app](https://github.com/Lekanlekzy/simple_web_app) to a dedicated **non-production** Azure App Service. Containers are optional. This code-deployment path does not require Docker, GHCR, or Trivy; those remain separate opt-in integrations. CI supports all six language profiles, while this first application-package deployment supports Node only.

## Application and caller contract

- The application has `lint`, `format:check`, `build`, and `test:ci` npm scripts. TypeScript callers also need `typecheck`. `test:ci` writes `coverage/lcov.info`, transferred to the isolated Sonar job.
- CI's `package_app` defaults to false and is supported only for Node. The sample enables it only after a PR merges into `main`. Its post-merge CI checks out the exact `github.sha` and verifies it equals the PR's `merge_commit_sha`; `package:ci` then creates a ready-to-run `deploy/` directory containing `package.json`, built assets, the server, and any production dependencies. Builds and dependency installation run without Azure credentials.
- CI stamps `release.json` with `{ "revision": "<git commit SHA>" }`, archives `deploy/` as `app.zip`, and records its SHA-256. Its successful required-checks job exposes `app_package_artifact_id`, `app_package_sha256`, and `app_revision` after every mandatory gate and requested container/publication job succeeds.
- The caller validates PR events `opened`, `synchronize`, and `reopened`; `closed` with `merged: true` reruns CI on the merged default-branch revision and then calls `reusable-app-cd.yml` with `needs: ci`, the three package outputs, and Azure inputs. Closed unmerged PRs skip. Manual dispatch runs validation only, and there is no push trigger. Same-repository PR heads are required; calls triggered by `dependabot[bot]` skip. Merged runs are not cancelled as superseded PR validation.
- CD requires a closed merged PR into the actual default branch (`main` in the sample), the matching default-branch ref, matching event/caller repositories, a non-fork repository, a same-repository PR head, and `github.sha` equal to the PR merge SHA. It downloads the exact same-run artifact and verifies its ZIP hash and release revision before Azure login; it never rebuilds the package. Sonar's post-merge CI scan explicitly targets the PR base branch rather than the closed PR.
- The caller lives at `.github/workflows/caller-ci-cd.yml`. A file directly under `.github/` is not a GitHub Actions workflow. Use [the Node caller example](../../examples/caller-workflows/node-app-ci-cd.yml.example).
- Only the CD caller and isolated deployment job allow `id-token: write`. The CI caller keeps its existing scopes for OSV, Gitleaks, and the optional image publisher, with no OIDC permission or Azure inputs. CD has no checkout, application build commands, or Sonar secret. The CI summary table and CD deployment/health summary report their own results.

## One-time Azure setup

Use the Azure portal or Cloud Shell for this initial setup. This repository does not create resources automatically.

1. Create a dedicated non-production App Service and plan: **Publish: Code**, **Linux**, **Node.js 24 LTS**. Use a globally unique app name and choose the region and plan for your account. Record the resource group and subscription. Review the plan's cost before creating it.
2. Set the startup command to `npm start`, enable HTTPS only, and set these application settings:

   ```text
   WEBSITE_RUN_FROM_PACKAGE=1
   SCM_DO_BUILD_DURING_DEPLOYMENT=false
   ```

   The package is built in CI, so Azure must not rebuild it. The sample server has no production npm dependencies and listens on Azure's `PORT` environment variable.
3. Create an Entra application/service principal or user-assigned identity with an OIDC federated credential:

   ```text
   Issuer:   https://token.actions.githubusercontent.com
   Subject:  repo:Lekanlekzy/simple_web_app:environment:non-production
   Audience: api://AzureADTokenExchange
   ```

   Assign **Website Contributor** scoped to this App Service resource, using the [official OIDC setup guide](https://learn.microsoft.com/en-us/azure/app-service/deploy-github-actions?tabs=openid). No Azure client secret or publish profile is required. Keep the identity scoped to this non-production application.
4. In the application repository, create the `non-production` GitHub Environment. Restrict deployment to the actual default branch and configure required reviewers where available. The Azure default deployment slot is named `production`; here it belongs to a dedicated non-production app, and no paid staging-slot feature is required.
5. Configure these **repository Actions variables** (the caller must read them before entering the reusable workflow):

   | Variable | Value |
   |---|---|
   | `SONAR_PROJECT_KEY` | Existing Sonar project for this application in `lekanlekzy` |
   | `AZURE_WEBAPP_NAME` | The dedicated non-production App Service name |
   | `AZURE_CLIENT_ID` | Federated identity client ID |
   | `AZURE_TENANT_ID` | Tenant ID |
   | `AZURE_SUBSCRIPTION_ID` | Subscription ID |

   Add the named `SONAR_TOKEN` repository secret with analysis permission for that project. IDs are configuration values; there is no Azure authentication secret to pass.
6. Commit both central reusable workflows before using the application's `@main` references. Commit the sample's caller, source, manifests, and lockfile. Generated `node_modules/`, `dist/`, `coverage/`, and `deploy/` must be untracked and ignored.

## Post-deployment health check

The sample exposes `GET /healthz`:

```json
{ "status": "ok", "revision": "<deployed commit SHA>" }
```

It returns HTTP 503 when the built page or its referenced assets are missing. It contains no credentials, configuration dump, or database status; this sample has no database.

CD retries for a five-minute startup window. It requires HTTPS, HTTP 200 from the JSON endpoint, `status` equal to `ok`, and `revision` equal to CI's packaged commit. It then requests `/` and requires HTTP 200 with a nonempty body. A stale version, unavailable app, or failed check fails CD, and `deployment_url` is exposed only after verification succeeds. A failed health check does not automatically roll back the deployment.

These checks answer three questions: can the server respond, is the expected release running, and can it serve the built page? The asset check catches incomplete packages; the revision check prevents an old but healthy deployment from passing; the retry window allows App Service startup. This is basic readiness and deployment verification. It does not exercise browser JavaScript or user journeys, and the sample has no database dependency to test.

The completed ZIP is not currently started and runtime-tested before deployment. Source tests and the production build run first; the deployed application is then verified by CD. Package checksums verify bytes, without establishing independent build provenance; SBOMs and provenance/attestation verification are planned for Stage 2.

## Manual rollback

Application packages are retained as `node-app-<run-id>-<attempt>` artifacts for 30 days, subject to repository retention settings. Select a previous successful **merged-PR release** run of this application's caller, with a successful CD/health result. Download that run's artifact from GitHub, including `app.zip` and `app.zip.sha256`.

From PowerShell, after authenticating to Azure with an authorized operator account:

```powershell
$actual = (Get-FileHash -LiteralPath .\rollback\app.zip -Algorithm SHA256).Hash.ToLowerInvariant()
$expected = (Get-Content -LiteralPath .\rollback\app.zip.sha256 -Raw).Trim()
if ($actual -ne $expected) { throw 'Rollback package checksum mismatch.' }
az webapp deploy --resource-group YOUR_RESOURCE_GROUP --name YOUR_NONPROD_APP --src-path .\rollback\app.zip --type zip
Invoke-RestMethod 'https://YOUR_APP_HOST/healthz'
```

Verify the returned revision matches the selected run's commit and check the home page. This redeploys the retained package without rebuilding it. Keep failed deployment evidence and record the rollback run, artifact hash, and resulting revision. Cloud deployment, health verification, and rollback need a real configured Azure run before acceptance is complete.
