# Single-machine PM Hub: `make run` starts the hub, server and dashboard; `make simulate` sends data.
SHELL := /bin/bash

MQTT_PORT      ?= 1884
DASHBOARD_PORT ?= 8501
PATIENTS       ?= 5
DURATION       ?= 300
export MQTT_PORT

VENV      := .venv
PY        := $(VENV)/bin/python
DASHBOARD := nurse_dashboard_local.py
PIDFILE   := .dashboard.pid

.PHONY: help run up dashboard simulate demo status logs stop clean

help:
	@echo "make run        start hub + server containers and the nurse dashboard"
	@echo "make simulate   send simulated vitals (PATIENTS=$(PATIENTS) DURATION=$(DURATION)s)"
	@echo "make demo       run + simulate"
	@echo "make status     show containers and dashboard state"
	@echo "make logs       follow the bridge logs"
	@echo "make stop       stop dashboard and containers (data kept)"
	@echo "make clean      stop and delete data volumes, venv and generated files"

.env:
	@umask 077; printf 'INFLUX_PASSWORD=%s\nHUB_TOKEN=%s\nSERVER_TOKEN=%s\n' \
		"$$(openssl rand -hex 12)" "$$(openssl rand -hex 32)" "$$(openssl rand -hex 32)" > $@
	@echo "Created $@ with new random tokens"

$(VENV): 
	python3 -m venv $(VENV)
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q paho-mqtt==2.1.0 influxdb-client==1.50.0 streamlit pandas pytz streamlit-autorefresh

$(DASHBOARD): ../scripts/nurse_dashboard/nurse_dashboard.py
	sed -e "s|http://<SERVER_IP>:8086|http://localhost:8087|" \
	    -e "s|\"<TOKEN>\"|__import__('os').environ['SERVER_TOKEN']|" $< > $@

up: .env
	docker compose up -d --build

dashboard: .env $(VENV) $(DASHBOARD)
	@if [ -f $(PIDFILE) ] && kill -0 $$(cat $(PIDFILE)) 2>/dev/null; then \
		echo "Dashboard already running (pid $$(cat $(PIDFILE)))"; \
	else \
		set -a; . ./.env; set +a; \
		nohup $(VENV)/bin/streamlit run $(DASHBOARD) --server.port $(DASHBOARD_PORT) \
			--server.headless true > dashboard.log 2>&1 & echo $$! > $(PIDFILE); \
		echo "Dashboard started (log: local/dashboard.log)"; \
	fi

run: up dashboard
	@echo "Nurse dashboard: http://localhost:$(DASHBOARD_PORT)   MQTT broker: localhost:$(MQTT_PORT)"
	@echo "Send data with: make simulate"

simulate: $(VENV)
	$(PY) ../scripts/patient_device/multi_channels_test.py --broker localhost \
		--port $(MQTT_PORT) --channels $(PATIENTS) --duration $(DURATION)

demo: run simulate

status:
	@docker compose ps --format '{{.Name}}\t{{.Status}}'
	@if [ -f $(PIDFILE) ] && kill -0 $$(cat $(PIDFILE)) 2>/dev/null; then \
		echo "dashboard: running (pid $$(cat $(PIDFILE))) on port $(DASHBOARD_PORT)"; \
	else echo "dashboard: stopped"; fi

logs:
	docker compose logs -f mqtt-influx-bridge

stop:
	@if [ -f $(PIDFILE) ]; then kill $$(cat $(PIDFILE)) 2>/dev/null || true; rm -f $(PIDFILE); fi
	docker compose down

clean: stop
	docker compose down -v
	rm -rf $(VENV) $(DASHBOARD) dashboard.log
