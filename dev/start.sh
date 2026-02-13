#!/bin/bash
set -euo pipefail

# Log everything to /var/log/ha.log while still printing to the console
LOGFILE="/var/log/ha.log"
touch "$LOGFILE" || true
exec > >(tee -a "$LOGFILE") 2>&1

WATCH_DIR="/config/custom_components"
DEBOUNCE=10

HA_CMD=(python -m homeassistant --config /config)
HA_PID=0

start_ha() {
	echo "Starting Home Assistant..."
	"${HA_CMD[@]}" &
	HA_PID=$!
	echo "Home Assistant started with PID $HA_PID"
}

stop_ha() {
	if [ "$HA_PID" -ne 0 ]; then
		echo "Stopping Home Assistant (PID $HA_PID)..."
		kill "$HA_PID" 2>/dev/null || true
		# wait up to 10s
		for i in {1..10}; do
			if kill -0 "$HA_PID" 2>/dev/null; then
				sleep 1
			else
				break
			fi
		done
		if kill -0 "$HA_PID" 2>/dev/null; then
			echo "Force killing Home Assistant (PID $HA_PID)"
			kill -9 "$HA_PID" 2>/dev/null || true
		fi
		wait "$HA_PID" 2>/dev/null || true
		HA_PID=0
	fi
}

trap 'echo "Received termination signal, stopping..."; stop_ha; exit 0' INT TERM EXIT

start_ha

# Use a file descriptor reading from inotifywait so we can debounce properly.
# Behavior: perform an immediate restart on the first event, then collect any
# additional events that arrive within $DEBOUNCE seconds and perform one
# additional restart if any were seen. This ensures we never miss updates but
# do restarts at most every $DEBOUNCE seconds for a burst of changes.
exec 3< <(inotifywait -m -r -e close_write,modify,create,delete --format '%w%f' "$WATCH_DIR")
while IFS= read -r -u 3 file; do
	# ignore changes in Python bytecode caches
	case "$file" in
	*/__pycache__*)
		continue
		;;
	esac
	echo "Change detected: $file -- restarting Home Assistant"
	stop_ha
	start_ha

	# Collect further events for up to $DEBOUNCE seconds. If we see any,
	# perform one additional restart after the quiet period.
	pending=0
	last_event="$file"
	while IFS= read -r -u 3 -t "$DEBOUNCE" next; do
		case "$next" in
		*/__pycache__*)
			continue
			;;
		esac
		echo "Queued change: $next"
		pending=1
		last_event="$next"
	done

	if [ "$pending" -eq 1 ]; then
		echo "Processing pending change: $last_event -- restarting Home Assistant"
		stop_ha
		start_ha
	fi
done

