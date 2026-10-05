.PHONY: start stop status dev-start dev-stop dev-status

start:
	bash deployment/scripts/jpdy.sh start

stop:
	bash deployment/scripts/jpdy.sh stop

status:
	bash deployment/scripts/jpdy.sh status

dev-start:
	bash deployment/scripts/jpdy.sh dev-start

dev-stop:
	bash deployment/scripts/jpdy.sh dev-stop

dev-status:
	bash deployment/scripts/jpdy.sh dev-status
