#!/bin/bash
LAST=""
while true; do
    CLIP=$(pbpaste 2>/dev/null | tr -d $'\n\r')
    if [[ "$CLIP" != "$LAST" ]] && [[ ${#CLIP} -gt 60 ]] && [[ "$CLIP" == *"#"* ]]; then
        RESULT=$(osascript /tmp/find_login_win.scpt 2>/dev/null)
        if [[ "$RESULT" == OK* ]]; then
            echo "$(date +%H:%M:%S) Auto-pasted to $RESULT"
            LAST="$CLIP"
        fi
    fi
    sleep 0.3
done
