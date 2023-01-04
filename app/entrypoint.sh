#!/bin/bash
service ssh start

uvicorn app.main:app --proxy-headers --host 0.0.0.0 --port 8000