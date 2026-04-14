tell application "iTerm2"
    set tok to do shell script "pbpaste | tr -d '\n\r'"
    set wcount to count of windows
    set wi to 1
    repeat with wi from 1 to wcount
        try
            set c to contents of current session of current tab of window wi
            if c contains "Paste code here if prompted" and c does not contain "claude_paste_daemon" then
                tell current session of current tab of window wi
                    write text tok
                end tell
                return "OK window " & wi
            end if
        end try
    end repeat
    return "not found"
end tell
