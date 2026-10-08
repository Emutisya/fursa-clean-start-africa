// Optional real-browser checks via an already running local Edge/Chromium CDP.
// Node 22+ only; no npm packages. See README for the two local endpoints.
import assert from "node:assert/strict";
import {mkdir, readFile, unlink} from "node:fs/promises";
import {resolve} from "node:path";

const app = process.argv[2] || "http://127.0.0.1:8769";
const debuggerUrl = process.argv[3] || "http://127.0.0.1:9229";
const pages = await (await fetch(`${debuggerUrl}/json/list`)).json();
const target = pages.find(page => page.type === "page");
assert(target, "Launch a headless browser with a remote debugging port first.");
const socket = new WebSocket(target.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
socket.onmessage = event => {
  const message = JSON.parse(event.data);
  if (!pending.has(message.id)) return;
  const {resolve, reject, timer} = pending.get(message.id);
  clearTimeout(timer); pending.delete(message.id);
  message.error ? reject(new Error(message.error.message)) : resolve(message.result);
};
await new Promise((resolve,reject) => { socket.onopen=resolve; socket.onerror=reject; });
function send(method, params={}) {
  return new Promise((resolve,reject) => {
    const next=++id;
    const timer=setTimeout(()=>{ pending.delete(next); reject(new Error(`Timeout: ${method}`)); },10000);
    pending.set(next,{resolve,reject,timer});
    socket.send(JSON.stringify({id:next,method,params}));
  });
}
async function evaluate(expression) {
  const result=await send("Runtime.evaluate",{expression,awaitPromise:true,returnByValue:true});
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function waitFor(expression) {
  await evaluate(`new Promise((resolve,reject)=>{
    const start=Date.now();
    const timer=setInterval(()=>{
      if(${expression}) { clearInterval(timer); resolve(true); }
      else if(Date.now()-start>5000) { clearInterval(timer); reject(new Error("UI condition timed out")); }
    },25);
  })`);
}
try {
  await send("Page.enable");
  await send("Page.navigate",{url:`${app}/?clawpilotTheme=light`});
  await waitFor(`document.querySelectorAll(".chip").length===13`);
  assert.equal(await evaluate(`document.documentElement.dataset.theme`),"light");
  await evaluate(`document.querySelector('[data-preset="workshop"]').click()`);
  await waitFor(`document.querySelectorAll(".match").length===2 && !document.getElementById("submit").disabled`);
  assert.match(await evaluate(`document.getElementById("results").textContent`),/Timber workshop/);
  assert.equal(await evaluate(`document.querySelector("#evidence input").checked`),true);
  await evaluate(`document.querySelector("#evidence input").click(); document.getElementById("form").requestSubmit()`);
  await waitFor(`document.querySelectorAll(".match").length===2 && !document.getElementById("submit").disabled`);
  assert.match(await evaluate(`document.getElementById("results").textContent`),/Synthetic carpentry work sample/);
  await evaluate(`document.querySelector('[data-preset="energy"]').click()`);
  await waitFor(`document.getElementById("results").textContent.includes("Solar maintenance") && !document.getElementById("submit").disabled`);
  await evaluate(`document.querySelector('[data-preset="enterprise"]').click()`);
  await waitFor(`document.getElementById("results").textContent.includes("accounts practice") && !document.getElementById("submit").disabled`);
  const downloadPath=resolve(".browser-check","exports");
  await mkdir(downloadPath,{recursive:true});
  const exportFile=resolve(downloadPath,"fursa-synthetic-passport.json");
  await send("Browser.setDownloadBehavior",{behavior:"allow",downloadPath});
  await evaluate(`document.getElementById("export").click()`);
  let passport;
  for(let attempt=0;attempt<50;attempt++) {
    try { passport=JSON.parse(await readFile(exportFile,"utf8")); break; }
    catch { await new Promise(resolve=>setTimeout(resolve,100)); }
  }
  assert(passport, "Synthetic passport download did not complete.");
  assert.equal(passport.synthetic,true);
  assert.equal(passport.credential_issued,false);
  assert.deepEqual(passport.skills,["bookkeeping","customer service","spreadsheets"]);
  await unlink(exportFile);
  await evaluate(`document.querySelector('[data-preset="unmatched"]').click()`);
  await waitFor(`document.getElementById("results").textContent.includes("No relevant catalogue match")`);
  await evaluate(`document.getElementById("skills").value=""; document.getElementById("skills").dispatchEvent(new Event("input")); document.getElementById("form").requestSubmit()`);
  assert.match(await evaluate(`document.getElementById("status").textContent`),/at least one/);
  await evaluate(`document.getElementById("skills").value="criminal history"; document.getElementById("form").requestSubmit()`);
  assert.equal(await evaluate(`document.getElementById("status").className`),"error");
  await evaluate(`document.getElementById("reset").click()`);
  assert.equal(await evaluate(`document.getElementById("skills").value`),"");
  await send("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=window.innerWidth`),true);
  await evaluate(`document.documentElement.dataset.theme="dark"`);
  assert.equal(await evaluate(`getComputedStyle(document.body).backgroundColor`),"rgb(61, 59, 58)");
  console.log("PASS: all presets, model-backed ranking, evidence gaps, synthetic export, no-match, invalid input, reset, mobile layout and both themes.");
} finally {
  socket.close();
}
