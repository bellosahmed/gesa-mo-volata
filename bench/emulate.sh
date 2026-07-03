#!/usr/bin/env bash
exec systemd-run --user --scope -p MemoryMax=7G -p MemorySwapMax=0 "$@"
