# Overview
If you are using a mac and install a lot of tools for coding and development, you can run into occassional space constraints 
due to downloading tools and models. If that is the case this is the right page for you.

# Best cleanup tool
https://github.com/tw93/mole

# Docker

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

# LM Studio models
```
Delete folders directly from ~/.lmstudio/models/ (older installs use ~/.cache/lm-studio/models/).
```
# Hugging face
```
# See which models and datasets are taking up space
huggingface-cli scan-cache

# Pick which ones to delete from a list
huggingface-cli delete-cache

rm -rf ~/.cache/huggingface/hub/
```
