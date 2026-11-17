// Plain-language messages for requests that fail without a Jigsaurium API error (issue #93).
//
// The API answers errors with JSON (`{"error": {"message": ...}}`), and those messages are shown
// as they are. Anything else, such as the reverse proxy's HTML page for a 502/503/504, a dropped
// connection or a timeout, gets a message from here that says what happened and whether to retry,
// instead of raw HTML. The raw response is logged to the browser console for diagnosis.
(() => {
  const CHECK_SAVED =
    "If you were saving something, check whether it was saved before trying again.";

  function messageForStatus(status) {
    const code = Number(status) || 0;
    if (code === 502 || code === 503 || code === 504) {
      return `The Jigsaurium server is not responding right now (error ${code}). It may be restarting or busy: wait a minute, then try again. ${CHECK_SAVED}`;
    }
    if (code === 401) {
      return "Your session has ended. Sign in again to continue.";
    }
    if (code === 403) {
      return "You do not have permission to do that (error 403).";
    }
    if (code === 404) {
      return "That item could not be found (error 404). It may have been deleted: refresh the page.";
    }
    if (code === 408) {
      return `The server took too long to answer (error 408). ${CHECK_SAVED}`;
    }
    if (code === 413) {
      return "That upload is too large for the server (error 413). Try a smaller file.";
    }
    if (code === 429) {
      return "Too many requests right now (error 429). Wait a moment, then try again.";
    }
    if (code >= 500) {
      return `Something went wrong on the server (error ${code}). Try again; if it keeps happening, tell an administrator.`;
    }
    return `The request failed (error ${code}). Try again; if it keeps happening, tell an administrator.`;
  }

  function networkFailureMessage() {
    return `Cannot reach the Jigsaurium server. Check your connection, then try again. ${CHECK_SAVED}`;
  }

  function timeoutMessage(seconds) {
    const after = seconds ? ` after ${seconds} seconds` : "";
    return `The server did not answer${after}. It may still finish the request. ${CHECK_SAVED}`;
  }

  // Logs what the server actually sent, without showing it to the user.
  function logRawFailure(path, status, responseText) {
    const snippet = String(responseText || "").replace(/\s+/g, " ").trim().slice(0, 300);
    console.warn(`Request to ${path} failed with HTTP ${status}.`, snippet ? `Response: ${snippet}` : "");
  }

  window.JigsauriumHttpErrors = Object.freeze({
    messageForStatus,
    networkFailureMessage,
    timeoutMessage,
    logRawFailure,
  });
})();
