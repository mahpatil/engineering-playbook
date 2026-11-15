# Cleanup: Reclaiming Disk Space on macOS

> A guide for managing disk space on macOS when you install many coding and development tools.

## Overview

If you use a Mac and install a lot of tools for coding and development, you can run into occasional space constraints due to downloading tools and models. If that is the case, this page is for you.

## Start with

Settings > General > Storage > Applications, Bin — clear all apps you don't use.

## Best cleanup tool

[Mole](https://github.com/tw93/mole)

## Docker

```sh
# See what's using space
docker system df -v

# Remove images no container is using (~6GB)
docker image prune -a

# Clear the build cache (the full ~7GB, not just the 38MB shown as reclaimable)
docker builder prune -a

# Remove volumes no container is using (~67MB, but check first: this deletes their data)
docker volume ls -f dangling=true
docker volume prune -a
```

## LM Studio models

Delete folders directly from `~/.lmstudio/models/` (older installs use `~/.cache/lm-studio/models/`).

## Hugging Face

```sh
# See which models and datasets are taking up space
huggingface-cli scan-cache

# Pick which ones to delete from a list
huggingface-cli delete-cache

rm -rf ~/.cache/huggingface/hub/
```
