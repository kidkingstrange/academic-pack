# Browser Agent & Chrome Remote Debugging Rule

## Managed Chrome Profile Requirement
Whenever browser control, browser subagents, or browser automation tasks are performed:
1. **Always use the managed profile**: Ensure Chrome runs with the dedicated Antigravity profile located at `%APPDATA%\Antigravity\ChromeProfile`, NOT the user's personal Chrome profile.
2. **Verify Port 9222 Before Automation**:
   - Check if port 9222 is active (`netstat -ano | findstr 9222`).
   - If port 9222 is not listening, automatically launch the managed Chrome instance in the background before initiating any browser operations:
     ```powershell
     Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList @(
         '--remote-debugging-port=9222',
         '--remote-allow-origins=*',
         ('--user-data-dir=' + $env:APPDATA + '\Antigravity\ChromeProfile'),
         '--no-first-run',
         '--no-default-browser-check'
     )
     ```
3. **Persist Session**: Keep the managed instance running so repeated browser commands reuse the active DevTools WebSocket connection.
