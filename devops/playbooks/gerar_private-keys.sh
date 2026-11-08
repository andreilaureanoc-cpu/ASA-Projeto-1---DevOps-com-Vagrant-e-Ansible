#!/bin/bash

ssh-keygen -t ed25519 -N "" -C "andrei@devops" -f ./keys/andrei
ssh-keygen -t ed25519 -N "" -C "gabriel@devops" -f ./keys/gabriel
