#!/usr/bin/env bash
# Manage the s2idd_auto QueueServer using the active Bluesky environment.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
QSERVER_DIR="${REPO_ROOT}/src/s2idd_auto/qserver"
ICONFIG_YML="${REPO_ROOT}/src/s2idd_auto/configs/iconfig.yml"

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export QS_CONFIG_YML="${QSERVER_DIR}/qs-config.yml"
STARTUP_DIR="${STARTUP_DIR:-${SCRIPT_DIR}}"
QS_HOSTNAME="${QS_HOSTNAME:-$(hostname)}"
CATALOG="${DATABROKER_CATALOG:-$(awk '/^DATABROKER_CATALOG:/ {print $NF; exit}' "${ICONFIG_YML}")}"
DEFAULT_SESSION_NAME="bluesky_queueserver-s2idd_auto-${CATALOG}"
SESSION_NAME="${2:-${DEFAULT_SESSION_NAME}}"
STARTUP_COMMAND=(
    start-re-manager
    "--config=${QS_CONFIG_YML}"
    "--user-group-permissions=${QSERVER_DIR}/user_group_permissions.yaml"
    "--existing-plans-devices=${QSERVER_DIR}/existing_plans_and_devices.yaml"
)

usage() {
    echo "Usage: $(basename "${BASH_SOURCE[0]}") {start|stop|restart|status|checkup|console|run} [NAME]"
    echo "Default screen session: ${DEFAULT_SESSION_NAME}"
    echo "Use console to attach; detach with Ctrl-A, D."
    echo "Use run to start QueueServer in the foreground for diagnostics."
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Required command '$1' not found; activate your Bluesky environment." >&2
        exit 1
    fi
}

find_session() {
    local sessions
    sessions=$(screen -ls 2>/dev/null || true)
    SCREEN_SESSION=$(awk -v name="${SESSION_NAME}" '
        $1 ~ /^[0-9]+\./ {
            session_name = $1
            sub(/^[0-9]+\./, "", session_name)
            if (session_name == name) { print $1; exit }
        }
    ' <<< "${sessions}")
    [[ -n "${SCREEN_SESSION}" ]]
}

start() {
    if find_session; then
        echo "${SCREEN_SESSION} is already running"
        return
    fi
    require_command start-re-manager
    cd "${STARTUP_DIR}"
    screen -dmS "${SESSION_NAME}" -h 5000 "${STARTUP_COMMAND[@]}"
    if find_session; then
        echo "Started ${SCREEN_SESSION}"
    else
        echo "QueueServer exited during startup. Use '$0 run' to inspect the error." >&2
        return 1
    fi
}

stop() {
    if find_session; then
        echo "Stopping ${SCREEN_SESSION}"
        screen -S "${SCREEN_SESSION}" -X quit
    else
        echo "${SESSION_NAME} is not running"
    fi
}

SELECTION="${1:-usage}"
case "${SELECTION}" in
    start|stop|kill|restart|status|checkup|console|run) ;;
    -h|--help|help|usage) usage; exit 0 ;;
    *) usage >&2; exit 1 ;;
esac

if [[ "$(hostname)" != "${QS_HOSTNAME}" ]]; then
    echo "Must manage QueueServer on ${QS_HOSTNAME}. This is $(hostname)." >&2
    exit 1
fi
require_command screen

case "${SELECTION}" in
    start) start ;;
    stop|kill) stop ;;
    restart) stop; sleep 0.1; start ;;
    status)
        if find_session; then
            echo "${SCREEN_SESSION} is running"
        else
            echo "${SESSION_NAME} is not running"
        fi
        ;;
    checkup) start ;;
    console)
        if find_session; then
            exec screen -x "${SCREEN_SESSION}"
        else
            echo "${SESSION_NAME} is not running" >&2
            exit 1
        fi
        ;;
    run)
        if find_session; then
            echo "${SCREEN_SESSION} is already running" >&2
            exit 1
        fi
        require_command start-re-manager
        cd "${STARTUP_DIR}"
        exec "${STARTUP_COMMAND[@]}"
        ;;
esac
