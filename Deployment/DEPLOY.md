# TCP Crypto AI Trader -- Google Cloud Deployment Guide

## Phase 1 -- Create Google Cloud VM

-   Create an Ubuntu 24.04 LTS VM.
-   Recommended: 2 vCPU, 4 GB RAM, 30 GB SSD.
-   Allow SSH access.
-   Update the OS after login.

## Phase 2 -- Upload Project

Clone your GitHub repository:

``` bash
git clone <YOUR_GITHUB_REPOSITORY>
cd tcp_crypto_ai_trader
```

Copy or create:

-   `.env`
-   `deployment/install.sh`
-   `deployment/start.sh`
-   `deployment/tcp_ai_trader.service`
-   `deployment/tcp_ai_trader.logrotate`

## Phase 3 -- Install

Run:

``` bash
chmod +x deployment/install.sh
./deployment/install.sh
```

Verify:

``` bash
python -m src.production_readiness_audit
python healthcheck.py
```

Both should complete successfully.

## Phase 4 -- Configure Service

``` bash
sudo cp deployment/tcp_ai_trader.service \
/etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable tcp_ai_trader.service
sudo systemctl start tcp_ai_trader.service
```

## Phase 5 -- Configure Log Rotation

``` bash
sudo cp deployment/tcp_ai_trader.logrotate \
/etc/logrotate.d/tcp_ai_trader
```

Test:

``` bash
sudo logrotate -d /etc/logrotate.d/tcp_ai_trader
```

## Phase 6 -- Verify

``` bash
sudo systemctl status tcp_ai_trader.service
tail -f logs/application.log
```

Confirm:

-   Market Stream starts
-   Recovery completes
-   Daily Scheduler starts
-   LINE startup notification arrives

## Phase 7 -- Forward Test

Run Paper Trading continuously for seven days.

Track:

-   Win Rate
-   Profit Factor
-   Expectancy
-   Drawdown
-   Margin Usage
-   Open Risk
-   Recovery
-   Daily Report
-   Dashboard
-   LINE alerts

Do not modify strategy during the seven-day forward test unless a
genuine software defect is found.