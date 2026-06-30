/**
 * Shared helpers for CelebrateVibes AE automation scripts.
 * No File.write calls — avoids AE "Allow Scripts to Write Files" requirement.
 */

function logLine(line) {
    $.writeln(line);
}

function quitAfterEffects() {
    try {
        app.quit(SaveOptions.DONOTSAVECHANGES);
    } catch (ignore) {}
}

function runScript(mainFn) {
    try {
        mainFn();
    } catch (error) {
        var message = error && error.toString ? error.toString() : String(error);
        logLine("ERROR: " + message);
        alert(message);
        throw error;
    } finally {
        quitAfterEffects();
    }
}
