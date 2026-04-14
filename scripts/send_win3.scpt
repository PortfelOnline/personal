tell application "iTerm2"
    set tok to do shell script "pbpaste | tr -d '\n\r'"
    tell current session of current tab of window 3
        write text tok
    end tell
end tell
