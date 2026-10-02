.PHONY: start stop status

start:
	bash deployment/scripts/jpdy.sh start

stop:
	bash deployment/scripts/jpdy.sh stop

status:
	bash deployment/scripts/jpdy.sh status
