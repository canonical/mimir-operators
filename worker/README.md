# Mimir Worker charm for Kubernetes

[![CharmHub Badge](https://charmhub.io/mimir-worker-k8s/badge.svg)](https://charmhub.io/mimir-worker-k8s)
[![Release](https://github.com/canonical/mimir-worker-k8s-operator/actions/workflows/release.yaml/badge.svg)](https://github.com/canonical/mimir-worker-k8s-operator/actions/workflows/release.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

## Description

The Mimir Worker charm provides a scalable long-term storage using [Mimir](https://github.com/grafana/mimir).
This charm is part of the Mimir HA deployment, and is meant to be deployed together with the [mimir-coordinator-k8s](https://github.com/canonical/mimir-coordinator-k8s-operator) charm.

A Mimir Worker can assume any role that the Mimir binary can take on, and it should always be related to a Mimir Coordinator.

## OCI Images

This charm by default uses the latest release of the [ubuntu/mimir](https://hub.docker.com/r/ubuntu/mimir/) image.
