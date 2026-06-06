# ⛵ HomeOps

This repository contains my Kubernetes homelab configuration, adapted from [onedr0p/cluster-template](https://github.com/onedr0p/cluster-template) and customized for my HomeOps environment. Whether you're running on bare-metal or virtual machines (VMs), the goal is to keep cluster operations reproducible and easy to iterate on.

At its core, this project leverages [makejinja](https://github.com/mirkolenz/makejinja), a powerful tool for rendering templates. By reading the [cluster.toml](./cluster.sample.toml) configuration file—validated and defaulted by [CUE](https://cuelang.org/)—Makejinja generates the necessary configurations to deploy a Kubernetes cluster with the following features:

- Easy configuration through a single TOML file.
- Compatibility with home setups, whether on physical hardware or VMs.
- A modular and extensible approach to cluster deployment and management.

With this approach, you'll gain a solid foundation to build and manage your Kubernetes cluster efficiently.

## ✨ Features

A Kubernetes cluster deployed with [Talos Linux](https://github.com/siderolabs/talos) and an opinionated implementation of [Flux](https://github.com/fluxcd/flux2) using [GitHub](https://github.com/) as the Git provider, [sops](https://github.com/getsops/sops) to manage secrets and the [Tailscale Kubernetes Operator](https://tailscale.com/kb/1236/kubernetes-operator) for secure remote access.

- **Required:** Some knowledge of [Containers](https://opencontainers.org/), [YAML](https://noyaml.com/), [Git](https://git-scm.com/), and access to a **Tailscale tailnet** where you can create OAuth clients.
- **Included components:** [flux](https://github.com/fluxcd/flux2), [cilium](https://github.com/cilium/cilium), [cert-manager](https://github.com/cert-manager/cert-manager), [spegel](https://github.com/spegel-org/spegel), [reloader](https://github.com/stakater/Reloader), and the [Tailscale Kubernetes Operator](https://tailscale.com/kb/1236/kubernetes-operator).

**Other features include:**

- Dev env managed w/ [mise](https://mise.jdx.dev/)
- Workflow automation w/ [GitHub Actions](https://github.com/features/actions)
- Dependency automation w/ [Renovate](https://www.mend.io/renovate)
- Flux `HelmRelease` and `Kustomization` diffs w/ [flux-local](https://github.com/allenporter/flux-local)

Does this sound cool to you? If so, continue to read on! 👇

## 🚀 Let's Go!

There are **6 stages** outlined below for completing this project, make sure you follow the stages in order.

### Stage 1: Hardware Configuration

For a **stable** and **high-availability** production Kubernetes cluster, hardware selection is critical. NVMe/SSDs are strongly preferred over HDDs, and **Bare Metal is strongly recommended** over virtualized platforms like Proxmox.

Using **enterprise NVMe or SATA SSDs on Bare Metal** (even used drives) provides the most reliable performance and rock-solid stability. Consumer **NVMe or SATA SSDs**, on the other hand, carry risks such as latency spikes, corruption, and fsync delays, particularly in multi-node setups.

**Proxmox with enterprise drives can work** for testing or carefully tuned production clusters, but it introduces additional layers of potential I/O contention — especially if consumer drives are used. Any **replicated storage** (e.g., Rook-Ceph, Longhorn) should always use **dedicated disks separate from control plane and etcd nodes** to ensure reliability. Worker nodes are more flexible, but risky configurations should still be avoided for stateful workloads to maintain cluster stability.

These guidelines provide a strong baseline, but there are always exceptions and nuances. The best way to ensure your hardware configuration works is to **test it thoroughly and benchmark performance** under realistic workloads.

### Stage 2: Machine Preparation

> [!IMPORTANT]
> If you have **3 or more nodes** it is recommended to make 3 of them controller nodes for a highly available control plane. This project configures **all nodes** to be able to run workloads. **Worker nodes** are therefore **optional**.
>
> **Minimum system requirements**
> | Role    | Cores    | Memory        | System Disk               |
> |---------|----------|---------------|---------------------------|
> | Control/Worker | 4 | 16GB | 256GB SSD/NVMe |

1. Head over to the [Talos Linux Image Factory](https://factory.talos.dev) and follow the instructions. Be sure to only choose the **bare-minimum system extensions** as some might require additional configuration and prevent Talos from booting without it. Depending on your CPU start with the Intel/AMD system extensions (`i915`, `intel-ucode` & `mei` **or** `amdgpu` & `amd-ucode`), you can always add system extensions after Talos is installed and working.

2. This will eventually lead you to download a Talos Linux ISO (or for SBCs a RAW) image. Make sure to note the **schematic ID** you will need this later on.

3. Flash the Talos ISO or RAW image to a USB drive and boot from it on your nodes.

4. Verify with `nmap` that your nodes are available on the network. (Replace `192.168.1.0/24` with the network your nodes are on.)

    ```sh
    nmap -Pn -n -p 50000 192.168.1.0/24 -vv | grep 'Discovered'
    ```

### Stage 3: Local Workstation

> [!TIP]
> It is recommended to set the visibility of your repository to `Public` so you can easily request help if you get stuck.

1. Clone this repository locally and change into the directory. For example:

    ```sh
    gh repo clone jckimble/homeops
    cd homeops
    ```

2. **Install** the [Mise CLI](https://mise.jdx.dev/getting-started.html#installing-mise-cli) on your local workstation.

3. **Activate** Mise in your shell by following the [activation guide](https://mise.jdx.dev/getting-started.html#activate-mise).

4. Use `mise` to install the **required** CLI tools:

    ```sh
    mise trust
    pip install pipx
    mise install
    ```

   📍 _**Having trouble installing the tools?** Try unsetting the `GITHUB_TOKEN` env var and then run these commands again_

   📍 _**Having trouble compiling Python?** Try running `mise settings python.compile=0` and then run these commands again_

5. Logout of the GitHub Container Registry as this may cause authorization problems in future steps when using the public registry:

    ```sh
    docker logout ghcr.io
    helm registry logout ghcr.io
    ```

### Stage 4: Tailscale configuration

> [!WARNING]
> If any of the commands fail with `command not found` or `unknown command` it means `mise` is either not installed, activated or it could be configured incorrectly.

1. Create a Tailscale OAuth client for the Kubernetes operator by following the [Tailscale install guide](https://tailscale.com/docs/kubernetes-operator/install-operator), then save the `client_id` and `client_secret` values for `cluster.toml`.

    - Ensure the OAuth client has the tags required by the operator (for example `tag:k8s-operator`).
    - Keep the generated credentials available while completing Stage 5.

### Stage 5: Cluster configuration

1. Generate the config files from the sample files:

    ```sh
    just init
    ```

2. Fill out the `cluster.toml` configuration file using the comments in it as a guide.

    - At minimum, populate your network, node, repository, and `[tailscale]` OAuth settings.

3. Template out the kubernetes and talos configuration files, if any issues come up be sure to read the error and adjust your config files accordingly.

    ```sh
    just configure
    ```

4. Push your changes to git:

   📍 _**Verify** all the `./kubernetes/**/*.sops.*` files are **encrypted** with SOPS_

    ```sh
    git add -A
    git commit -m "chore: initial commit :rocket:"
    git push
    ```

> [!TIP]
> Using a **private repository**? Make sure to paste the public key from `github-deploy.key.pub` into the deploy keys section of your GitHub repository settings. This will make sure Flux has read/write access to your repository.

### Stage 6: Bootstrap Talos, Kubernetes, and Flux

> [!WARNING]
> It might take a while for the cluster to be setup (10+ minutes is normal). During which time you will see a variety of error messages like: "couldn't get current server API group list," "error: no matching resources found", etc. 'Ready' will remain "False" as no CNI is deployed yet. **This is normal.** If this step gets interrupted, e.g. by pressing <kbd>Ctrl</kbd> + <kbd>C</kbd>, you likely will need to [reset the cluster](#-reset) before trying again

1. Install Talos:

    ```sh
    just bootstrap talos
    ```

2. Push your changes to git:

    ```sh
    git add -A
    git commit -m "chore: add talhelper encrypted secret :lock:"
    git push
    ```

3. Install cilium, coredns, spegel, flux and sync the cluster to the repository state:

    ```sh
    just bootstrap apps
    ```

4. Watch the rollout of your cluster happen:

    ```sh
    kubectl get pods --all-namespaces --watch
    ```

## 📣 Post installation

### ✅ Verifications

1. Check the status of Cilium:

    ```sh
    kubectl -n kube-system exec ds/cilium --container cilium-agent -- cilium status
    ```

2. Check the status of Flux and if the Flux resources are up-to-date and in a ready state:

   📍 _Run `just kube reconcile` to force Flux to sync your Git repository state_

    ```sh
    flux check
    flux get sources git flux-system
    flux get ks -A
    flux get hr -A
    ```

3. Check TCP connectivity to Tailscale ingress endpoints:

   📍 _The variables are only placeholders, replace them with your actual values_

    ```sh
    nmap -Pn -n -p 443 echo.${tailnet}.ts.net -vv
    ```

4. Check you can reach `echo` over Tailscale:

   📍 _The variables are only placeholders, replace them with your actual values_

    ```sh
    curl -I https://echo.${tailnet}.ts.net
    ```

5. Check Tailscale ingress status:

    ```sh
    kubectl get ingress -A
    ```

### 🌐 Tailscale Access

> [!TIP]
> Services exposed with `ingressClassName: tailscale` are reachable at `https://<hostname>.<tailnet>.ts.net`.

By default, `echo` is exposed over Tailscale at `echo.<tailnet>.ts.net`.

### ➕ Exposing New Apps

To expose any new app at `https://<service>.<tailnet>.ts.net`, add a standard Kubernetes `Ingress` with `ingressClassName: tailscale` and a `tailscale.com/hostname` annotation.

Example:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
    name: my-app
    annotations:
        tailscale.com/hostname: my-app
spec:
    ingressClassName: tailscale
    defaultBackend:
        service:
            name: my-app
            port:
                number: 80
```

This publishes `https://my-app.<tailnet>.ts.net` on default HTTPS without router port forwarding.

### 🪝 Git Reconciliation

Flux reconciles on its polling interval by default. This repository does not expose a public webhook endpoint.

If you want faster convergence after a push, you can run:

```sh
just kube reconcile
```

## 💥 Reset

> [!CAUTION]
> **Resetting** the cluster **multiple times in a short period of time** could lead to being **rate limited by container registries**.

There might be a situation where you want to destroy your Kubernetes cluster. The following command will reset your nodes back to maintenance mode.

```sh
just talos reset
```

## 🛠️ Talos and Kubernetes Maintenance

### ⚙️ Updating Talos node configuration

> [!TIP]
> Ensure you have updated `talconfig.yaml` and any patches with your updated configuration. In some cases you **not only need to apply the configuration but also upgrade talos** to apply new configuration.

```sh
# (Re)generate the Talos config
just talos generate-config
# Apply the config to the node
just talos apply-node <ip>
# e.g. just talos apply-node 10.10.10.10
```

### ⬆️ Updating Talos and Kubernetes versions

> [!TIP]
> Ensure the `talosVersion` and `kubernetesVersion` in `talenv.yaml` are up-to-date with the version you wish to upgrade to.

```sh
# (Re)generate the Talos config
just talos generate-config
# Apply the config to the node
just talos apply-node <ip>
# e.g. just talos apply-node 10.10.10.10
just talos upgrade-node <ip>
# e.g. just talos upgrade-node 10.10.10.10
```

```sh
# Upgrade cluster to a newer Kubernetes version
just talos upgrade-k8s
```

### ➕ Adding a node to your cluster

At some point you might want to expand your cluster to run more workloads and/or improve the reliability of your cluster. Keep in mind it is recommended to have an **odd number** of control plane nodes for quorum reasons.

You don't need to re-bootstrap the cluster to add new nodes. Follow these steps:

1. **Prepare the new node**: Review the [Stage 2: Machine Preparation](#stage-2-machine-preparation) section and boot your new node into maintenance mode.

2. **Get the node information**: While the node is in maintenance mode, retrieve the disk and MAC address information needed for configuration:

   ```sh
   talosctl get disks -n <ip> --insecure
   talosctl get links -n <ip> --insecure
   ```

3. **Update the configuration**: Read the documentation for [talhelper](https://budimanjojo.github.io/talhelper/latest/) and extend the `talconfig.yaml` file manually with the new node information (including the disk and MAC address from step 2).

4. **Generate and apply the configuration**:

   ```sh
   # Render your talosconfig based on the talconfig.yaml file
   just talos generate-config

   # Apply the configuration to the node
   just talos apply-node <ip>
   # e.g. just talos apply-node 10.10.10.10
   ```

The node should join the cluster automatically and workloads will be scheduled once they report as ready.

## 🤖 Renovate

[Renovate](https://www.mend.io/renovate) is a tool that automates dependency management. It is designed to scan your repository around the clock and open PRs for out-of-date dependencies it finds. Common dependencies it can discover are Helm charts, container images, GitHub Actions and more! In most cases merging a PR will cause Flux to apply the update to your cluster.

To enable Renovate, click the 'Configure' button over at their [Github app page](https://github.com/apps/renovate) and select your repository. Renovate creates a "Dependency Dashboard" as an issue in your repository, giving an overview of the status of all updates. The dashboard has interactive checkboxes that let you do things like advance scheduling or reattempt update PRs you closed without merging.

The base Renovate configuration in your repository can be viewed at [.renovaterc.json5](.renovaterc.json5). By default it is scheduled to be active with PRs every weekend, but you can [change the schedule to anything you want](https://docs.renovatebot.com/presets-schedule), or remove it if you want Renovate to open PRs immediately.

## 🐛 Debugging

Below is a general guide on trying to debug an issue with an resource or application. For example, if a workload/resource is not showing up or a pod has started but in a `CrashLoopBackOff` or `Pending` state. These steps do not include a way to fix the problem as the problem could be one of many different things.

1. Check if the Flux resources are up-to-date and in a ready state:

   📍 _Run `just kube reconcile` to force Flux to sync your Git repository state_

    ```sh
    flux get sources git -A
    flux get ks -A
    flux get hr -A
    ```

2. Do you see the pod of the workload you are debugging:

    ```sh
    kubectl -n <namespace> get pods -o wide
    ```

3. Check the logs of the pod if it's there:

    ```sh
    kubectl -n <namespace> logs <pod-name> -f
    ```

4. If a resource exists, try to describe it to see what problems it might have:

    ```sh
    kubectl -n <namespace> describe <resource> <name>
    ```

5. Check the namespace events:

    ```sh
    kubectl -n <namespace> get events --sort-by='.metadata.creationTimestamp'
    ```

Resolving problems that you have could take some tweaking of your YAML manifests in order to get things working, other times it could be a external factor like permissions on a NFS server. If you are unable to figure out your problem see the support sections below.

## 🧹 Tidy up

Once your cluster is fully configured and you no longer need to run `just configure`, it's a good idea to clean up the repository by removing the [template](./template) directory and any files related to the templating process. This helps reduce clutter and resolves any "duplicate registry" warnings from Renovate.

1. Tidy up your repository:

    ```sh
    just template tidy
    ```

2. Push your changes to git:

    ```sh
    git add -A
    git commit -m "chore: tidy up :broom:"
    git push
    ```

## ❔ What's next

There's a lot to absorb here, especially if you're new to these tools. Take some time to familiarize yourself with the tooling and understand how all the components interconnect. Dive into the documentation of the various tools included — they are a valuable resource. This shouldn't be a production environment yet, so embrace the freedom to experiment. Move fast, break things intentionally, and challenge yourself to fix them.

Below are some optional considerations you may want to explore.

### DNS

For non-Tailscale exposure patterns, you can add a separate ingress controller and DNS automation later. This is optional for the default tailscale-first workflow in this repository.

External-DNS offers broad support for various DNS providers, including but not limited to:

- [Pi-hole](https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/pihole.md)
- [UniFi](https://github.com/kashalls/external-dns-unifi-webhook)
- [Adguard Home](https://github.com/muhlba91/external-dns-provider-adguard)
- [Bind](https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/rfc2136.md)

This flexibility allows you to integrate seamlessly with a range of DNS solutions to suit your environment and offload DNS from your cluster to your router, or external device.

### Secrets

SOPS is an excellent tool for managing secrets in a GitOps workflow. However, it can become cumbersome when rotating secrets or maintaining a single source of truth for secret items.

For a more streamlined approach to those issues, consider [External Secrets](https://external-secrets.io/latest/). This tool allows you to move away from SOPs and leverage an external provider for managing your secrets. External Secrets supports a wide range of providers, from cloud-based solutions to self-hosted options.

### Storage

If your workloads require persistent storage with features like replication or connectivity to NFS, SMB, or iSCSI servers, there are several projects worth exploring:

- [rook-ceph](https://github.com/rook/rook) / [longhorn](https://github.com/longhorn/longhorn) / [openebs](https://github.com/openebs/openebs)
- [democratic-csi](https://github.com/democratic-csi/democratic-csi)
- [csi-driver-nfs](https://github.com/kubernetes-csi/csi-driver-nfs) / [csi-driver-smb](https://github.com/kubernetes-csi/csi-driver-smb)
- [synology-csi](https://github.com/SynologyOpenSource/synology-csi)
- [truenas-csi](https://github.com/truenas/truenas-csi) / [tns-csi](https://github.com/fenio/tns-csi)

These tools offer a variety of solutions to meet your persistent storage needs, whether you’re using cloud-native or self-hosted infrastructures.

### Community Repositories

Community member [@whazor](https://github.com/whazor) created [Kubesearch](https://kubesearch.dev) to allow searching Flux HelmReleases across Github and Gitlab repositories with the `kubesearch` topic.

## 🙋 Support

### Community

- Make a post in this repository's GitHub [Discussions](https://github.com/jckimble/homeops/discussions).
- Start a thread in the `#support` channel in the [Home Operations](https://discord.gg/home-operations) Discord server.

## 📺 Media

Check out these videos below. If you find them helpful, a like and subscribe goes a long way!

<a href="https://youtube.com/watch?v=aeUKOpeoiUs">
  <img src="https://github.com/user-attachments/assets/2dab1c6f-7b27-4b94-a7ad-a6d9c5b17c78" alt="Youtube Video" width="300">
</a>
&nbsp;&nbsp;
<a href="https://youtube.com/watch?v=hoi2GzvJUXM">
  <img src="https://github.com/user-attachments/assets/5b939b90-0019-4515-b90c-321ffe7448cf" alt="Youtube Video" width="300">
</a>

## 🙌 Related Projects

If this repo is too hot to handle or too cold to hold check out these following projects.

- [ajaykumar4/cluster-template](https://github.com/ajaykumar4/cluster-template) - _A template for deploying a Talos Kubernetes cluster including Argo for GitOps_
- [mitchross/k3s-argocd-starter](https://github.com/mitchross/k3s-argocd-starter) - starter kit for k3s, argocd
- [ricsanfre/pi-cluster](https://github.com/ricsanfre/pi-cluster) - _Pi Kubernetes Cluster. Homelab kubernetes cluster automated with Ansible and FluxCD_
- [techno-tim/k3s-ansible](https://github.com/techno-tim/k3s-ansible) - _The easiest way to bootstrap a self-hosted High Availability Kubernetes cluster. A fully automated HA k3s etcd install with kube-vip, MetalLB, and more. Build. Destroy. Repeat._

## ⭐ Stargazers

<div align="center">

<a href="https://star-history.com/#jckimble/homeops&Date">
  <picture>
        <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=jckimble/homeops&type=Date&theme=dark" />
        <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=jckimble/homeops&type=Date" />
        <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=jckimble/homeops&type=Date" />
  </picture>
</a>

</div>

## 🤝 Thanks

Big shout out to all the contributors, sponsors and everyone else who has helped on this project.
