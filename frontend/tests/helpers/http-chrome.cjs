"use strict";
// Chrome/CDP lifecycle reused from the existing F02 HTTP regression. No npm dependencies.
const fs = require("node:fs"), os = require("node:os"), path = require("node:path");
const {spawn, spawnSync} = require("node:child_process");
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
function waitForProcessExit(child, timeoutMs) {
  return new Promise(resolve => {
    if (child.exitCode !== null || child.signalCode !== null) { resolve(true); return; }
    let timer;
    const onExit = () => { clearTimeout(timer); resolve(true); };
    timer = setTimeout(() => { child.off("exit", onExit); resolve(false); }, timeoutMs);
    child.once("exit", onExit);
  });
}
function signalChromeTree(child,signal){
  // Chrome's Linux helper processes must be stopped with their isolated group.
  // Windows retains the normal process termination path.
  if(process.platform!=="win32"&&Number.isInteger(child.pid)){
    try{process.kill(-child.pid,signal);return;}
    catch(error){if(error.code!=="ESRCH")throw error;}
  }
  if(child.exitCode===null&&child.signalCode===null)child.kill(signal);
}
async function removeProfileAfterChromeExit(profile){
  // Chrome's helper processes can still flush files after the launcher exits.
  // A failed removal is a test failure, never a reason to claim browser PASS.
  const transient=new Set(["ENOTEMPTY","EBUSY","EPERM","EACCES"]);
  for(let attempt=0;attempt<15;attempt++){
    try{
      await fs.promises.rm(profile,{recursive:true,force:true,maxRetries:3,retryDelay:200});
      if(!fs.existsSync(profile))return;
    }catch(error){
      if(!transient.has(error.code)||attempt===14)throw error;
    }
    await wait(300);
  }
  throw Error("Chrome profile remains after bounded cleanup retries: "+profile);
}
async function stopChrome(child,profile,ws=null){
  if(ws){try{ws.close();}catch{/* Chrome may already be terminating. */}}
  if(child.exitCode===null&&child.signalCode===null){
    signalChromeTree(child,"SIGTERM");
    if(!await waitForProcessExit(child,4000)){
      signalChromeTree(child,"SIGKILL");
      if(!await waitForProcessExit(child,4000)){
        throw Error("Chrome did not exit; refusing to remove an active browser profile");
      }
    }
  }
  // The launcher can exit while Chrome helpers still hold the profile/pipe.
  if(process.platform!=="win32")signalChromeTree(child,"SIGTERM");
  if(ws&&ws.readyState!==WebSocket.CLOSED){
    await Promise.race([
      new Promise(resolve=>ws.addEventListener("close",resolve,{once:true})),
      wait(1500),
    ]);
  }
  await removeProfileAfterChromeExit(profile);
}

function browserBinary() {
  for (const name of [process.env.F01_BROWSER_BIN, process.env.CHROME_BIN,
    "/usr/bin/google-chrome", "/usr/bin/chromium", "google-chrome", "chromium"].filter(Boolean)) {
    // Absolute Windows paths use backslashes; a Unix-only slash/which test misses Chrome.
    const filePath = path.isAbsolute(name) || name.includes("/") || name.includes("\\");
    if (filePath && fs.existsSync(name)) return name;
    if (!filePath && spawnSync(process.platform === "win32" ? "where" : "which", [name]).status === 0) return name;
  }
  return null;
}
async function launchChrome(bin) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "f01-scenario-chrome-"));
  const child = spawn(bin, ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
    "--disable-background-networking", "--no-first-run", "--remote-debugging-port=0",
    "--user-data-dir=" + profile, "about:blank"], { stdio: ["ignore", "ignore", "pipe"], detached: process.platform !== "win32" });
  let diagnostics = "";
  child.stderr.on("data", x => { diagnostics = (diagnostics + x.toString()).slice(-1000); });
  let ws = null;
  try {
    let port = 0;
    for (let i = 0; i < 300; i++) {
      const active = path.join(profile, "DevToolsActivePort");
      try {
        const candidate = Number(fs.readFileSync(active, "utf8").split("\n")[0]);
        if (Number.isInteger(candidate) && candidate > 0) {port = candidate;break;}
      } catch (error) {
        // Windows can briefly lock this file while Chrome writes it.
        // Keep the existing 30s bound; a persistent failure still fails.
        if (!["ENOENT", "EBUSY", "EPERM", "EACCES"].includes(error.code)) throw error;
      }
      if (child.exitCode !== null) throw Error("Chrome exited: " + diagnostics);
      await wait(100);
    }
    if (!port) throw Error("Chrome CDP startup timed out: " + diagnostics);
    const targets = await (await fetch("http://127.0.0.1:" + port + "/json/list", { signal: AbortSignal.timeout(10000) })).json();
    const page = targets.find(x => x.type === "page" && x.webSocketDebuggerUrl);
    if (!page) throw Error("Chrome CDP page unavailable");
    ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(Error("CDP WebSocket open timed out")), 12000);
      ws.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
      ws.addEventListener("error", () => { clearTimeout(timer); reject(Error("CDP WebSocket failed")); }, { once: true });
    });
    let nextId = 0;
    const pending = new Map();
    const exceptions = [];
    const outbound = [];
    ws.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") {
        exceptions.push(message.params.exceptionDetails.exception?.description ||
          message.params.exceptionDetails.text);
      }
      if (message.method === "Network.requestWillBeSent") outbound.push(message.params.request.url);
      if (!pending.has(message.id)) return;
      const task = pending.get(message.id);
      pending.delete(message.id);
      message.error ? task.reject(Error(message.error.message)) : task.resolve(message.result);
    });
    ws.addEventListener("close", () => {
      for (const task of pending.values()) task.reject(Error("CDP WebSocket closed"));
      pending.clear();
    });
    const command = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(Error("CDP command timed out: " + method));
      }, 15000);
      pending.set(id, {
        resolve: value => { clearTimeout(timer); resolve(value); },
        reject: error => { clearTimeout(timer); reject(error); },
      });
      try { ws.send(JSON.stringify({ id, method, params })); }
      catch (error) { pending.delete(id); clearTimeout(timer); reject(error); }
    });
    const evaluate = async expression => {
      const result = await command("Runtime.evaluate",
        { expression, returnByValue: true, awaitPromise: true });
      if (result.exceptionDetails) {
        throw Error("Browser JavaScript: " +
          (result.exceptionDetails.exception?.description || result.exceptionDetails.text));
      }
      return result.result.value;
    };
    return { profile, child, ws, command, evaluate, exceptions, outbound };
  } catch (error) {
    await stopChrome(child, profile, ws);
    throw error;
  }
}
async function waitUntil(evaluate, expression, description) {
  for (let i = 0; i < 100; i++) {
    try { if (await evaluate(expression)) return; } catch { /* navigating */ }
    await wait(100);
  }
  throw Error("Timed out waiting for " + description);
}
module.exports = {browserBinary, launchChrome, stopChrome, waitUntil};

