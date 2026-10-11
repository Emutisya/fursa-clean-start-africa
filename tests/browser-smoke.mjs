// Optional real-browser checks via an already running local Edge/Chromium CDP.
// Node 22+ only; no npm packages. See README for the two local endpoints.
import assert from "node:assert/strict";
import {mkdir, readFile, unlink, writeFile} from "node:fs/promises";
import {resolve} from "node:path";
import {execFile} from "node:child_process";
import {promisify} from "node:util";

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
  await evaluate(`window.savedPrint=window.print; window.print=()=>{window.printCalled=true;}; document.getElementById("print-review").click()`);
  assert.equal(await evaluate(`window.printCalled`),true);
  assert.match(await evaluate(`document.getElementById("review-print").textContent`),/Unverified simulation/);
  await send("Emulation.setEmulatedMedia",{media:"print"});
  assert.equal(await evaluate(`getComputedStyle(document.querySelector("main")).display`),"none");
  assert.equal(await evaluate(`getComputedStyle(document.getElementById("review-print")).display`),"block");
  await send("Emulation.setEmulatedMedia",{media:"screen"});
  await evaluate(`window.dispatchEvent(new Event("afterprint")); window.print=window.savedPrint`);
  assert.equal(await evaluate(`document.getElementById("review-print").childNodes.length`),0);
  assert.equal(await evaluate(`document.querySelector("#evidence input").checked`),true);
  await evaluate(`document.querySelector("#evidence input").click(); document.getElementById("form").requestSubmit()`);
  await waitFor(`document.querySelectorAll(".match").length===2 && !document.getElementById("submit").disabled`);
  assert.match(await evaluate(`document.getElementById("results").textContent`),/Synthetic carpentry work sample/);
  await evaluate(`document.querySelector('[data-preset="energy"]').click()`);
  await waitFor(`document.getElementById("results").textContent.includes("Solar maintenance") && !document.getElementById("submit").disabled`);
  await evaluate(`document.querySelector(".match details summary").focus()`);
  assert.equal(await evaluate(`document.activeElement.tagName`),"SUMMARY");
  await send("Input.dispatchKeyEvent",{type:"keyDown",key:"Enter",code:"Enter",text:"\r",windowsVirtualKeyCode:13});
  await send("Input.dispatchKeyEvent",{type:"keyUp",key:"Enter",code:"Enter",windowsVirtualKeyCode:13});
  await waitFor(`document.querySelector(".match details").open`);
  assert(await evaluate(`document.querySelectorAll('table[data-contributions="o-solar"] tbody tr').length>6`));
  assert.equal(await evaluate(`document.querySelector("table th").scope`),"col");
  await evaluate(`document.querySelector('[data-preset="enterprise"]').click()`);
  await waitFor(`document.getElementById("results").textContent.includes("accounts practice") && !document.getElementById("submit").disabled`);
  const downloadPath=process.argv[4] ? resolve(process.argv[4]) : resolve(".browser-check","exports");
  await mkdir(downloadPath,{recursive:true});
  const exportFile=resolve(downloadPath,"fursa-synthetic-passport.json");
  try {
    await readFile(exportFile);
    throw new Error("Refusing to overwrite an existing smoke-test export; choose a fresh artifact directory.");
  } catch(error) {
    if(error.code!=="ENOENT") throw error;
  }
  await send("Browser.setDownloadBehavior",{behavior:"allow",downloadPath});
  await evaluate(`document.getElementById("export").click()`);
  let passport;
  for(let attempt=0;attempt<50;attempt++) {
    try { passport=JSON.parse(await readFile(exportFile,"utf8")); break; }
    catch { await new Promise(resolve=>setTimeout(resolve,100)); }
  }
  assert(passport, "Synthetic passport download did not complete.");
  assert.equal(passport.synthetic,true);
  assert.equal(passport.schema,"fursa.synthetic-passport.v1");
  assert.equal(passport.verification,"Unverified synthetic selections");
  assert.deepEqual(passport.skills,["bookkeeping","customer service","spreadsheets"]);
  const imported=await promisify(execFile)("python",["-m","fursa","import-passport",exportFile],{timeout:10000});
  assert.equal(JSON.parse(imported.stdout).opportunities[0].id,"o-accounts");
  await evaluate(`document.getElementById("reset").click(); window.importRequests=0; window.importFetch=window.fetch;
    window.fetch=(...args)=>{window.importRequests++;return window.importFetch(...args);}`);
  const tree=await send("DOM.getDocument");
  const upload=await send("DOM.querySelector",{nodeId:tree.root.nodeId,selector:"#passport-import"});
  await send("DOM.setFileInputFiles",{nodeId:upload.nodeId,files:[exportFile]});
  await waitFor(`document.getElementById("status").textContent.includes("Validated unverified")`);
  assert.equal(await evaluate(`document.getElementById("skills").value`),"bookkeeping, customer service, spreadsheets");
  assert.equal(await evaluate(`window.importRequests`),0);
  assert.equal(await evaluate(`document.getElementById("export").disabled`),true);
  const invalidPassports=[
    JSON.stringify({...passport,name:"synthetic rejected field"}),
    JSON.stringify(passport).replace('"synthetic":true','"synthetic":false,"synthetic":true'),
    Buffer.from([255,254,0])
  ];
  for(let index=0;index<invalidPassports.length;index++) {
    const invalidFile=resolve(downloadPath,`invalid-passport-${index}.json`);
    await writeFile(invalidFile,invalidPassports[index],{flag:"wx"});
    await evaluate(`document.getElementById("status").textContent=""`);
    await send("DOM.setFileInputFiles",{nodeId:upload.nodeId,files:[invalidFile]});
    await waitFor(`document.getElementById("status").textContent.includes("Cannot import")`);
    assert.equal(await evaluate(`document.getElementById("skills").value`),"bookkeeping, customer service, spreadsheets");
    assert.equal(await evaluate(`window.importRequests`),0);
    await unlink(invalidFile);
  }
  await evaluate(`window.fetch=window.importFetch`);
  await unlink(exportFile);
  await evaluate(`document.querySelector('[data-preset="unmatched"]').click()`);
  await waitFor(`document.getElementById("results").textContent.includes("No relevant catalogue match")`);
  assert.match(await evaluate(`document.querySelector("[data-query-diagnostics]").textContent`),/without opportunities: astronomy/);
  assert.equal(await evaluate(`document.querySelectorAll("[data-query-diagnostics] code").length`),3);
  await evaluate(`document.querySelector('[data-recovery="skills"]').click()`);
  assert.equal(await evaluate(`document.activeElement.id`),"skills");
  await evaluate(`window.invalidRequests=0; window.savedFetch=window.fetch;
    window.fetch=(...args)=>{if(args[0]==="/api/match") window.invalidRequests++; return window.savedFetch(...args);}`);
  await evaluate(`document.getElementById("skills").value=""; document.getElementById("skills").dispatchEvent(new Event("input")); document.getElementById("form").requestSubmit()`);
  assert.match(await evaluate(`document.getElementById("status").textContent`),/at least one/);
  await evaluate(`document.getElementById("skills").value="criminal history"; document.getElementById("form").requestSubmit()`);
  assert.equal(await evaluate(`document.getElementById("status").className`),"error");
  assert.equal(await evaluate(`document.getElementById("skills").getAttribute("aria-invalid")`),"true");
  assert.equal(await evaluate(`document.activeElement.id`),"skills");
  assert.equal(await evaluate(`window.invalidRequests`),0);
  await evaluate(`window.fetch=window.savedFetch`);
  await evaluate(`document.getElementById("reset").click()`);
  assert.equal(await evaluate(`document.getElementById("skills").value`),"");
  assert.equal(await evaluate(`document.getElementById("skills").getAttribute("aria-invalid")`),"false");
  assert.equal(await evaluate(`document.getElementById("print-review").disabled`),true);
  await evaluate(`window.savedFetch=window.fetch; window.fetch=(url,options)=>{
    if(url!=="/api/match") return window.savedFetch(url,options);
    return new Promise(resolve=>{window.finishDelayed=()=>window.savedFetch(url,{...options,signal:undefined}).then(resolve);});
  }; document.getElementById("skills").value="solar"; document.getElementById("form").requestSubmit();`);
  assert.equal(await evaluate(`document.getElementById("results").getAttribute("aria-busy")`),"true");
  assert.equal(await evaluate(`document.getElementById("cancel").hidden`),false);
  await send("Input.dispatchKeyEvent",{type:"keyDown",key:"Escape",code:"Escape",windowsVirtualKeyCode:27});
  await send("Input.dispatchKeyEvent",{type:"keyUp",key:"Escape",code:"Escape",windowsVirtualKeyCode:27});
  await waitFor(`document.getElementById("status").textContent.includes("Inference cancelled")`);
  assert.equal(await evaluate(`document.activeElement.id`),"submit");
  await evaluate(`window.finishDelayed().then(()=>new Promise(resolve=>setTimeout(resolve,100)))`);
  assert.equal(await evaluate(`document.querySelectorAll(".match").length`),0);
  assert.equal(await evaluate(`document.getElementById("export").disabled`),true);
  assert.equal(await evaluate(`document.getElementById("skills").value`),"solar");
  await evaluate(`window.fetch=window.savedFetch; document.getElementById("reset").click()`);
  await evaluate(`document.querySelector('[data-skill="carpentry"]').focus()`);
  await send("Input.dispatchKeyEvent",{type:"keyDown",key:"ArrowRight",code:"ArrowRight",windowsVirtualKeyCode:39});
  await send("Input.dispatchKeyEvent",{type:"keyUp",key:"ArrowRight",code:"ArrowRight",windowsVirtualKeyCode:39});
  assert.equal(await evaluate(`document.activeElement.dataset.skill`),"welding");
  await send("Input.dispatchKeyEvent",{type:"keyDown",key:"Enter",code:"Enter",text:"\r",windowsVirtualKeyCode:13});
  await send("Input.dispatchKeyEvent",{type:"keyUp",key:"Enter",code:"Enter",windowsVirtualKeyCode:13});
  assert.equal(await evaluate(`document.getElementById("skills").value`),"welding");
  assert.equal(await evaluate(`document.activeElement.dataset.skill`),"welding");
  assert.equal(await evaluate(`[...document.querySelectorAll(".chip")].filter(button=>button.tabIndex===0).length`),1);
  await evaluate(`document.getElementById("reset").click()`);
  await evaluate(`document.getElementById("browse-panel").open=true; document.getElementById("browse-load").click()`);
  await waitFor(`document.querySelectorAll(".catalog-item").length===9`);
  await evaluate(`document.querySelector('[data-detail="o-accounts"]').click()`);
  await waitFor(`document.getElementById("resource-title").textContent.includes("accounts practice") && document.getElementById("resource-content").getAttribute("aria-busy")==="false"`);
  assert.equal(await evaluate(`document.getElementById("resource-dialog").open`),true);
  assert.equal(await evaluate(`document.querySelectorAll("[data-detail-evidence] li").length`),2);
  await send("Input.dispatchKeyEvent",{type:"keyDown",key:"Escape",code:"Escape",windowsVirtualKeyCode:27});
  await send("Input.dispatchKeyEvent",{type:"keyUp",key:"Escape",code:"Escape",windowsVirtualKeyCode:27});
  await waitFor(`!document.getElementById("resource-dialog").open`);
  assert.equal(await evaluate(`document.activeElement.dataset.detail`),"o-accounts");
  await evaluate(`document.querySelector('[data-compare-selection="o-accounts"]').click(); document.querySelector('[data-compare-selection="o-dispatch"]').click(); document.getElementById("compare-load").click()`);
  await waitFor(`document.querySelector("table[data-comparison]")`);
  assert.match(await evaluate(`document.getElementById("compare-status").textContent`),/spreadsheets/);
  assert.equal(await evaluate(`document.querySelectorAll("table[data-comparison] thead th").length`),3);
  await evaluate(`["o-water","o-metal","o-timber"].forEach(id=>document.querySelector('[data-compare-selection="'+id+'"]').click())`);
  assert.equal(await evaluate(`document.querySelectorAll("#compare-tray button").length`),4);
  assert.match(await evaluate(`document.getElementById("compare-status").textContent`),/limit reached/);
  await evaluate(`document.getElementById("reset").click()`);
  assert.equal(await evaluate(`document.querySelectorAll("#compare-tray button").length`),0);
  assert.equal(await evaluate(`document.querySelector("table[data-comparison]")`),null);
  assert.equal(await evaluate(`document.getElementById("skills").value`),"");
  await evaluate(`document.getElementById("browse-kind").value="pathway"; document.getElementById("browse-kind").dispatchEvent(new Event("change")); document.getElementById("browse-load").click()`);
  await waitFor(`document.querySelectorAll(".catalog-item").length===12`);
  await evaluate(`document.getElementById("browse-skill").value="astronomy"; document.getElementById("browse-skill").dispatchEvent(new Event("change")); document.getElementById("browse-load").click()`);
  await waitFor(`document.getElementById("browse-status").textContent.includes("No resources")`);
  assert.equal(await evaluate(`document.querySelectorAll(".catalog-item").length`),0);
  await send("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=window.innerWidth`),true);
  await evaluate(`document.documentElement.dataset.theme="dark"`);
  assert.equal(await evaluate(`getComputedStyle(document.body).backgroundColor`),"rgb(61, 59, 58)");
  console.log("PASS: all presets, model-backed ranking, evidence gaps, synthetic export, no-match, invalid input, reset, mobile layout and both themes.");
} finally {
  socket.close();
}
