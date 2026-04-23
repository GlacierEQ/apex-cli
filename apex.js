#!/usr/bin/env node
/**
 * APEX CLI v3.0.0 — MAXIMUM INTELLIGENCE EDITION
 * Autonomous Perplexity EXecution Engine
 * GlacierEQ / Casey Barton · Honolulu, Hawaii
 * Claude · GitHub · Supabase · Legal · Memory · Web
 */
import Anthropic from "@anthropic-ai/sdk";
import readline from "readline";
import fs from "fs";
import path from "path";
import os from "os";
import https from "https";
import { execSync } from "child_process";

const VERSION = "3.0.0";
const CONFIG_DIR = path.join(os.homedir(), ".apex-cli");
const PATHS = {
  config:  path.join(CONFIG_DIR, "config.json"),
  history: path.join(CONFIG_DIR, "history.jsonl"),
  session: path.join(CONFIG_DIR, "session.json"),
  memory:  path.join(CONFIG_DIR, "memory.json"),
  plugins: path.join(CONFIG_DIR, "plugins"),
  logs:    path.join(CONFIG_DIR, "logs"),
};

const C = {
  reset:"\x1b[0m",bold:"\x1b[1m",dim:"\x1b[2m",
  red:"\x1b[31m",green:"\x1b[32m",yellow:"\x1b[33m",
  blue:"\x1b[34m",cyan:"\x1b[36m",white:"\x1b[97m",
  gray:"\x1b[90m",orange:"\x1b[38;5;208m",teal:"\x1b[38;5;73m",
  gold:"\x1b[38;5;220m",purple:"\x1b[38;5;135m",
  bgDark:"\x1b[48;5;234m",
};

const APEX_SYSTEM = `You are APEX v3 — the most advanced autonomous AI execution engine built for Casey Barton (GlacierEQ), system architect, father, justice agent, Honolulu Hawaii.

## CORE DIRECTIVES
- NEVER summarize — always deliver actionable tactical intelligence
- NEVER hedge — provide decisive, precise, expert-level analysis  
- ALWAYS cite statutes, case law, and sources with precision
- ALWAYS assign P0/P1/P2 priorities to action items
- ALWAYS think 3 moves ahead strategically

## LEGAL INTELLIGENCE (ALWAYS ACTIVE)
Case: 1FDV-23-0001009 — Hawaii Family Court, High-Conflict Custody
Strategy: CONSTITUTIONAL WARFARE + FEDERAL ESCALATION
Weapons:
  - 42 U.S.C. §1983 (civil rights) → SOL: 2yr per HRS §657-7
  - 18 U.S.C. §1961-1968 RICO → Civil SOL: 4yr
  - HRS §601-7 (judicial disqualification — MANDATORY)
  - HRS §571-46 (custody best interests)
  - HRS §571-46.4 (parental alienation factors)
  - 14th Amendment + Troxel v. Granville (530 U.S. 57)
  - HRS §657-1.5 (discovery rule — SOL tolled)
Goal: REUNIFICATION WITH KEKOA

## TECHNICAL STACK
- GitHub: GlacierEQ org (660+ repos)
- Supabase: APEX memory backend (53 tables)
- MCP: perplexity-enhancement-mcp, mem0-mcp-integration

## OUTPUT FORMAT
Use markdown. Bold **critical items**. P0/P1/P2 everything.
Code blocks for all code. Tables for comparisons/timelines.`;

// Storage
const Store = {
  init() { [CONFIG_DIR,PATHS.plugins,PATHS.logs].forEach(d=>{if(!fs.existsSync(d))fs.mkdirSync(d,{recursive:true});});},
  load(f,d={}) { try{return fs.existsSync(f)?JSON.parse(fs.readFileSync(f,"utf8")):d;}catch{return d;} },
  save(f,data) { fs.writeFileSync(f,JSON.stringify(data,null,2)); },
  append(f,line) { fs.appendFileSync(f,JSON.stringify(line)+"\n"); },
  loadLines(f,n=50) { if(!fs.existsSync(f))return []; return fs.readFileSync(f,"utf8").trim().split("\n").slice(-n).map(l=>{try{return JSON.parse(l);}catch{return null;}}).filter(Boolean); }
};

// Memory Engine
const Memory = {
  data:{},
  load() { this.data=Store.load(PATHS.memory,{facts:[],context:{},legal:{},code:{}}); },
  save() { Store.save(PATHS.memory,this.data); },
  addFact(fact) { if(!this.data.facts)this.data.facts=[]; this.data.facts.push({fact,timestamp:new Date().toISOString()}); if(this.data.facts.length>500)this.data.facts=this.data.facts.slice(-500); this.save(); },
  remember(cat,key,val) { if(!this.data[cat])this.data[cat]={}; this.data[cat][key]={value:val,timestamp:new Date().toISOString()}; this.save(); },
  getContext() { const facts=(this.data.facts||[]).slice(-20).map(f=>f.fact).join("; "); return facts?`APEX Memory: ${facts}`:""; },
  stats() { return {facts:(this.data.facts||[]).length,categories:Object.keys(this.data).length}; }
};

// GitHub Client
const GitHub = {
  async api(endpoint,token,method="GET",body=null) {
    return new Promise((resolve,reject)=>{
      const opts={hostname:"api.github.com",path:endpoint,method,headers:{"Authorization":`Bearer ${token}`,"User-Agent":"APEX-CLI/3.0.0","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28",...(body?{"Content-Type":"application/json"}:{})}};
      const req=https.request(opts,res=>{let d="";res.on("data",c=>d+=c);res.on("end",()=>{try{resolve(JSON.parse(d));}catch{resolve(d);}});});
      req.on("error",reject);
      if(body)req.write(JSON.stringify(body));
      req.end();
    });
  },
  async getRepos(t){return this.api("/user/repos?per_page=30&sort=updated",t);},
  async getIssues(t,o,r){return this.api(`/repos/${o}/${r}/issues?state=open&per_page=10`,t);},
  async createIssue(t,o,r,title,body,labels=[]){return this.api(`/repos/${o}/${r}/issues`,t,"POST",{title,body,labels});},
  async getCommits(t,o,r){return this.api(`/repos/${o}/${r}/commits?per_page=5`,t);},
  async searchRepos(t,q){return this.api(`/search/repositories?q=${encodeURIComponent(q)}&per_page=10`,t);},
};

// Supabase Client
const Supabase = {
  async select(url,key,table,limit=10) {
    return new Promise((resolve,reject)=>{
      const opts={hostname:new URL(url).hostname,path:`/rest/v1/${table}?limit=${limit}`,method:"GET",headers:{"apikey":key,"Authorization":`Bearer ${key}`,"Accept":"application/json"}};
      const req=https.request(opts,res=>{let d="";res.on("data",c=>d+=c);res.on("end",()=>{try{resolve(JSON.parse(d));}catch{resolve(d);}});});
      req.on("error",reject);req.end();
    });
  }
};

// Display Engine
const Display = {
  clear(){process.stdout.write("\x1bc");},
  banner(){
    console.log(`\n${C.teal}${C.bold}  ╔══════════════════════════════════════════════════════════════╗
  ║   APEX CLI v3.0.0 — MAXIMUM INTELLIGENCE EDITION            ║
  ║   Autonomous Perplexity EXecution Engine · GlacierEQ        ║
  ║   Claude · GitHub · Supabase · Legal · Memory · Web         ║
  ╚══════════════════════════════════════════════════════════════╝${C.reset}\n`);
  },
  badge(ctx){
    const b={legal:`${C.bgDark}${C.orange}${C.bold} ⚖ LEGAL ${C.reset}`,code:`${C.bgDark}${C.cyan}${C.bold} ⌨ CODE  ${C.reset}`,apex:`${C.bgDark}${C.teal}${C.bold} ◈ APEX  ${C.reset}`,general:`${C.bgDark}${C.gray}${C.bold} ◇ GEN   ${C.reset}`,intel:`${C.bgDark}${C.gold}${C.bold} ◎ INTEL ${C.reset}`,github:`${C.bgDark}${C.purple}${C.bold} ⎇ GIT   ${C.reset}`,db:`${C.bgDark}${C.green}${C.bold} ▣ DB    ${C.reset}`};
    return b[ctx]||b.general;
  },
  thinking(msg="Processing"){
    const fr=["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"];let i=0;
    const iv=setInterval(()=>{process.stdout.write(`\r  ${C.teal}${fr[i++%fr.length]}${C.reset} ${C.gray}${msg}...${C.reset}`);},80);
    return()=>{clearInterval(iv);process.stdout.write("\r"+" ".repeat(50)+"\r");};
  },
  table(headers,rows){
    const w=headers.map((h,i)=>Math.max(h.length,...rows.map(r=>String(r[i]||"").length)));
    const sep="  +"+w.map(x=>"-".repeat(x+2)).join("+")+"+";
    const row=(cells,cc=C.white)=>"  |"+cells.map((c,i)=>` ${cc}${String(c||"").padEnd(w[i])}${C.reset} `).join("|")+"|";
    console.log(sep);console.log(row(headers,C.teal+C.bold));console.log(sep);
    rows.forEach(r=>console.log(row(r)));console.log(sep);
  },
  row(l,v,lc=C.gray,vc=C.white){console.log(`  ${lc}${l.padEnd(20)}${C.reset}${vc}${v}${C.reset}`);},
  status(l,ok,d=""){const ic=ok?`${C.green}✓`:`${C.red}✗`;console.log(`  ${ic}${C.reset} ${C.white}${l.padEnd(25)}${C.reset}${C.gray}${d}${C.reset}`);},
  ts(){return new Date().toLocaleTimeString("en-US",{hour:"2-digit",minute:"2-digit",second:"2-digit",timeZone:"Pacific/Honolulu"});},
  date(){return new Date().toLocaleDateString("en-US",{weekday:"short",month:"short",day:"numeric",year:"numeric",timeZone:"Pacific/Honolulu"});}
};

const COMMANDS = {"/legal":{d:"Deep Hawaii+federal legal analysis",c:"AI"},"/case":{d:"1FDV-23-0001009 war room brief",c:"AI"},"/motion":{d:"Draft legal motion [type]",c:"AI"},"/timeline":{d:"SOL watchpoints + deadline calendar",c:"AI"},"/strategy":{d:"Strategic war room analysis",c:"AI"},"/code":{d:"Production code generation",c:"AI"},"/apex":{d:"Full APEX orchestration",c:"AI"},"/intel":{d:"Multi-source intelligence brief",c:"AI"},"/scan":{d:"System audit + gap analysis",c:"AI"},"/daily":{d:"APEX daily intelligence briefing",c:"AI"},"/analyze":{d:"Deep analysis of any topic",c:"AI"},"/github":{d:"GitHub: repos|issues|commits|search",c:"INT"},"/db":{d:"Supabase: select [table]",c:"INT"},"/memory":{d:"Memory: show|remember|clear",c:"INT"},"/run":{d:"Execute shell command",c:"INT"},"/context":{d:"Switch context mode",c:"SES"},"/model":{d:"Switch AI model",c:"SES"},"/status":{d:"Full system status dashboard",c:"SES"},"/save":{d:"Save session to file",c:"SES"},"/load":{d:"Load session from file",c:"SES"},"/history":{d:"Recent query history",c:"SES"},"/clear":{d:"Clear session + screen",c:"SES"},"/key":{d:"Set Anthropic API key",c:"CFG"},"/ghkey":{d:"Set GitHub token",c:"CFG"},"/sburl":{d:"Set Supabase URL",c:"CFG"},"/sbkey":{d:"Set Supabase key",c:"CFG"},"/config":{d:"Show configuration",c:"CFG"},"/help":{d:"Show command reference",c:"CFG"},"/exit":{d:"Exit (auto-saves)",c:"CFG"}};

function printHelp(){
  const cat={AI:C.teal,INT:C.cyan,SES:C.yellow,CFG:C.gray};
  const names={AI:"AI COMMANDS",INT:"INTEGRATIONS",SES:"SESSION",CFG:"CONFIG"};
  ["AI","INT","SES","CFG"].forEach(c=>{
    console.log(`\n  ${cat[c]}${C.bold}${names[c]}${C.reset}`);
    Object.entries(COMMANDS).filter(([,v])=>v.c===c).forEach(([cmd,{d}])=>console.log(`  ${cat[c]}${cmd.padEnd(14)}${C.reset}${C.white}${d}${C.reset}`));
  });
  console.log();
}

async function printStatus(config,messages,context,model){
  console.log(`\n  ${C.teal}${C.bold}APEX SYSTEM STATUS${C.reset}  ${C.gray}${Display.date()} ${Display.ts()} HST${C.reset}\n`);
  Display.row("Version",`APEX CLI v${VERSION}`);
  Display.row("Context",context.toUpperCase());
  Display.row("Model",model);
  Display.row("Session msgs",String(messages.length));
  const ms=Memory.stats();
  Display.row("Memory facts",String(ms.facts));
  console.log();
  Display.status("Anthropic API",!!config.apiKey,config.apiKey?`···${config.apiKey.slice(-6)}`:"NOT SET — /key sk-ant-...");
  Display.status("GitHub Token",!!config.ghToken,config.ghToken?`GlacierEQ ···${config.ghToken.slice(-6)}`:"NOT SET — /ghkey ghp_...");
  Display.status("Supabase URL",!!config.sbUrl,config.sbUrl?config.sbUrl.slice(8,40)+"…":"NOT SET — /sburl https://...");
  Display.status("Supabase Key",!!config.sbKey,config.sbKey?`···${config.sbKey.slice(-6)}`:"NOT SET — /sbkey eyJ...");
  Display.status("Memory Store",true,`${ms.facts} facts · ${ms.categories} categories`);
  console.log();
}

async function handleGitHub(args,config){
  if(!config.ghToken){console.log(`\n  ${C.red}✗ /ghkey ghp_...${C.reset}\n`);return null;}
  const [sub,...rest]=(args||"repos").split(" ");
  const stop=Display.thinking("GitHub");
  try{
    if(sub==="repos"){const r=await GitHub.getRepos(config.ghToken);stop();if(Array.isArray(r)){console.log(`\n  ${C.teal}${C.bold}GlacierEQ Repos${C.reset}\n`);Display.table(["Repo","Lang","Stars","Updated"],r.slice(0,12).map(x=>[x.name,x.language||"—",x.stargazers_count,x.updated_at?.slice(0,10)]));}return null;}
    if(sub==="issues"){const[o,r]=(rest[0]||"GlacierEQ/apex-cli").split("/");const issues=await GitHub.getIssues(config.ghToken,o,r||"apex-cli");stop();if(Array.isArray(issues)&&issues.length)issues.forEach(i=>console.log(`  ${C.yellow}#${i.number}${C.reset} ${i.title}`));else console.log(`\n  ${C.gray}No open issues.${C.reset}\n`);return null;}
    if(sub==="commits"){const[o,r]=(rest[0]||"GlacierEQ/apex-cli").split("/");const commits=await GitHub.getCommits(config.ghToken,o,r||"apex-cli");stop();if(Array.isArray(commits))commits.forEach(c=>console.log(`  ${C.gold}${c.sha?.slice(0,7)}${C.reset} ${c.commit?.message?.split("\n")[0]?.slice(0,60)} ${C.gray}${c.commit?.author?.date?.slice(0,10)}${C.reset}`));return null;}
    if(sub==="search"){const q=rest.join(" ")||"apex";const res=await GitHub.searchRepos(config.ghToken,`${q} user:GlacierEQ`);stop();if(res.items)res.items.forEach(r=>console.log(`  ${C.cyan}${r.full_name}${C.reset} — ${C.gray}${r.description||"—"}${C.reset}`));return null;}
    if(sub==="create-issue"){const title=rest.join(" ")||"APEX Issue";const res=await GitHub.createIssue(config.ghToken,"GlacierEQ","apex-cli",title,`Created by APEX CLI v${VERSION}`,["apex"]);stop();if(res.number)console.log(`\n  ${C.green}✓ Issue #${res.number}: ${res.html_url}${C.reset}\n`);return null;}
    stop();return null;
  }catch(e){stop();console.log(`\n  ${C.red}✗ GitHub: ${e.message}${C.reset}\n`);return null;}
}

async function handleSupabase(args,config){
  if(!config.sbUrl||!config.sbKey){console.log(`\n  ${C.red}✗ /sburl + /sbkey required${C.reset}\n`);return null;}
  const[sub,...rest]=(args||"status").split(" ");
  const stop=Display.thinking("Supabase");
  try{
    if(sub==="select"||sub==="get"){const table=rest[0]||"apex_task_queue";const rows=await Supabase.select(config.sbUrl,config.sbKey,table);stop();if(Array.isArray(rows)&&rows.length){const keys=Object.keys(rows[0]).slice(0,5);Display.table(keys,rows.slice(0,8).map(r=>keys.map(k=>String(r[k]||"").slice(0,20))));}else console.log(`\n  ${C.gray}No data.${C.reset}\n`);return null;}
    stop();return null;
  }catch(e){stop();console.log(`\n  ${C.red}✗ Supabase: ${e.message}${C.reset}\n`);return null;}
}

function handleMemory(args){
  const[sub,...rest]=(args||"show").split(" ");
  if(sub==="show"||!sub){const ms=Memory.stats();console.log(`\n  ${C.teal}Memory: ${ms.facts} facts${C.reset}\n`);(Memory.data.facts||[]).slice(-10).forEach(f=>console.log(`  ${C.gray}·${C.reset} ${f.fact}`));console.log();return null;}
  if(sub==="remember"||sub==="add"){const fact=rest.join(" ");Memory.addFact(fact);console.log(`\n  ${C.green}✓ Remembered: "${fact}"${C.reset}\n`);return null;}
  if(sub==="clear"){Memory.data={facts:[],context:{},legal:{},code:{}};Memory.save();console.log(`\n  ${C.yellow}Memory cleared.${C.reset}\n`);return null;}
  return `[Memory: ${sub} ${rest.join(" ")}]`;
}

async function streamResponse(client,messages,model,memCtx=""){
  const sys=memCtx?`${APEX_SYSTEM}\n\n## MEMORY\n${memCtx}`:APEX_SYSTEM;
  const s=await client.messages.stream({model,max_tokens:8192,system:sys,messages});
  let full="";
  process.stdout.write(`\n  ${C.teal}${C.bold}◈ APEX${C.reset} ${C.gray}[${Display.ts()} HST]${C.reset}\n\n  `);
  for await(const chunk of s){
    if(chunk.type==="content_block_delta"&&chunk.delta.type==="text_delta"){
      const t=chunk.delta.text;full+=t;
      process.stdout.write(`${C.white}${t.replace(/\n/g,"\n  ")}${C.reset}`);
    }
  }
  process.stdout.write("\n\n");
  return full;
}

async function main(){
  Store.init();Memory.load();Display.clear();Display.banner();
  const config=Store.load(PATHS.config,{});
  let session=Store.load(PATHS.session,{messages:[],context:"apex"});
  let messages=session.messages||[];
  let context=session.context||"apex";
  let model=config.model||"claude-opus-4-5";
  let client=(config.apiKey||process.env.ANTHROPIC_API_KEY)?new Anthropic({apiKey:config.apiKey||process.env.ANTHROPIC_API_KEY}):null;
  if(process.env.ANTHROPIC_API_KEY&&!config.apiKey)config.apiKey=process.env.ANTHROPIC_API_KEY;

  await printStatus(config,messages,context,model);
  if(!client)console.log(`  ${C.yellow}  ⚡ /key sk-ant-... to start${C.reset}\n`);
  else console.log(`  ${C.gray}  Type message or ${C.yellow}/help${C.gray} · ${C.teal}/case${C.gray} for war room · ${C.teal}/daily${C.gray} for briefing${C.reset}\n`);

  const rl=readline.createInterface({
    input:process.stdin,output:process.stdout,terminal:true,
    completer:(line)=>{const hits=Object.keys(COMMANDS).filter(c=>c.startsWith(line));return[hits.length?hits:Object.keys(COMMANDS),line];}
  });
  const sp=()=>{rl.setPrompt(`\n  ${Display.badge(context)} ${C.teal}${C.bold}›${C.reset} `);rl.prompt();};
  sp();

  rl.on("line",async(raw)=>{
    const input=raw.trim();
    if(!input){sp();return;}
    Store.append(PATHS.history,{input,timestamp:new Date().toISOString(),context});

    if(input==="/exit"||input==="/quit"){Store.save(PATHS.session,{messages,context});console.log(`\n  ${C.teal}${C.bold}APEX${C.reset} ${C.gray}For Kekoa. Justice never sleeps.${C.reset}\n`);process.exit(0);}
    if(input==="/help"){printHelp();sp();return;}
    if(input==="/clear"){Display.clear();Display.banner();messages=[];sp();return;}
    if(input==="/status"){await printStatus(config,messages,context,model);sp();return;}
    if(input==="/config"){console.log(`\n`);Object.entries(config).forEach(([k,v])=>Display.row(k,typeof v==="string"&&v.length>20?v.slice(0,8)+"···"+v.slice(-6):String(v)));console.log();sp();return;}
    if(input==="/history"){const ls=Store.loadLines(PATHS.history,20);console.log(`\n  ${C.teal}History:${C.reset}\n`);ls.forEach((e,i)=>console.log(`  ${C.gray}${String(i+1).padStart(2)}.${C.reset} ${e.input} ${C.gray}${e.timestamp?.slice(0,16)}${C.reset}`));console.log();sp();return;}
    if(input.startsWith("/key "))      {config.apiKey=input.slice(5).trim();Store.save(PATHS.config,config);client=new Anthropic({apiKey:config.apiKey});console.log(`\n  ${C.green}✓ API key saved${C.reset}\n`);sp();return;}
    if(input.startsWith("/ghkey "))    {config.ghToken=input.slice(7).trim();Store.save(PATHS.config,config);console.log(`\n  ${C.green}✓ GitHub token saved${C.reset}\n`);sp();return;}
    if(input.startsWith("/sburl "))    {config.sbUrl=input.slice(7).trim();Store.save(PATHS.config,config);console.log(`\n  ${C.green}✓ Supabase URL saved${C.reset}\n`);sp();return;}
    if(input.startsWith("/sbkey "))    {config.sbKey=input.slice(7).trim();Store.save(PATHS.config,config);console.log(`\n  ${C.green}✓ Supabase key saved${C.reset}\n`);sp();return;}
    if(input.startsWith("/model "))    {model=input.slice(7).trim();config.model=model;Store.save(PATHS.config,config);console.log(`\n  ${C.green}✓ Model: ${C.cyan}${model}${C.reset}\n`);sp();return;}
    if(input.startsWith("/context ")) {context=input.slice(9).trim();console.log(`\n  ${C.green}✓ ${Display.badge(context)}${C.reset}\n`);sp();return;}
    if(input.startsWith("/save"))      {const f=input.slice(5).trim()||`apex-${Date.now()}.json`;fs.writeFileSync(f,JSON.stringify({messages,context,timestamp:new Date().toISOString()},null,2));console.log(`\n  ${C.green}✓ Saved: ${f}${C.reset}\n`);sp();return;}
    if(input.startsWith("/load"))      {const f=input.slice(5).trim();if(fs.existsSync(f)){const s=JSON.parse(fs.readFileSync(f,"utf8"));messages=s.messages||[];context=s.context||"apex";}else console.log(`\n  ${C.red}✗ Not found${C.reset}\n`);sp();return;}
    if(input.startsWith("/run "))      {try{const o=execSync(input.slice(5),{encoding:"utf8",timeout:10000});console.log(`\n${C.gray}${o}${C.reset}`);}catch(e){console.log(`\n  ${C.red}✗ ${e.message}${C.reset}\n`);}sp();return;}
    if(input.startsWith("/memory"))   {const r=handleMemory(input.slice(7).trim());if(!r){sp();return;}}
    if(input.startsWith("/github"))   {const r=await handleGitHub(input.slice(7).trim(),config);if(!r){sp();return;}}
    if(input.startsWith("/db"))       {const r=await handleSupabase(input.slice(3).trim(),config);if(!r){sp();return;}}

    if(!client){console.log(`\n  ${C.red}✗ /key sk-ant-...${C.reset}\n`);sp();return;}

    let msg=input;
    const d=Display.date(),ts=Display.ts();
    if(input==="/case") msg=`Deliver COMPLETE WAR ROOM BRIEF for 1FDV-23-0001009:\n1. Procedural posture\n2. P0 motions THIS WEEK (HRS §571-46, §601-7)\n3. Federal escalation readiness (§1983 predicates, RICO pattern)\n4. SOL countdown table\n5. Kekoa reunification — 3 immediate steps\n6. Evidence preservation requirements\n7. Constitutional violations to document NOW\nNo hedging. P0/P1/P2 everything.`;
    else if(input.startsWith("/legal "))    msg=`[LEGAL] ${input.slice(7)}\nCite: HRS, USC, Hawaii case law, SCOTUS. Actionable P0/P1/P2 steps.`;
    else if(input.startsWith("/motion "))   msg=`Draft complete legal motion: ${input.slice(8)}\nInclude: caption, intro, legal standard, argument with statute cites, prayer for relief. Hawaii Family Court format.`;
    else if(input.startsWith("/timeline")) msg=`COMPLETE SOL + DEADLINE CALENDAR for 1FDV-23-0001009:\n§1983 (HRS §657-7), RICO civil 4yr, HRS family deadlines, next hearings, evidence deadlines.\nFormat as table: Date | Deadline | Statute | Priority.`;
    else if(input.startsWith("/strategy")) msg=`[WAR ROOM STRATEGY] ${input.slice(9)||"Full APEX strategy"}\n3-move chess thinking. Legal+technical+strategic vectors. P0/P1/P2.`;
    else if(input.startsWith("/code "))     msg=`[PRODUCTION CODE] ${input.slice(6)}\nProduction-grade, error handling, TypeScript types if applicable. APEX/Supabase/GitHub patterns.`;
    else if(input.startsWith("/apex "))     msg=`[APEX ORCHESTRATION] ${input.slice(6)}\nConsider: Supabase (53 tables), GitHub (GlacierEQ 660+ repos), MCP servers, legal case.`;
    else if(input.startsWith("/intel "))    msg=`[INTELLIGENCE BRIEF] ${input.slice(7)}\nExecutive summary, key facts, tactical implications, recommended actions.`;
    else if(input.startsWith("/scan"))      msg=`APEX SYSTEM AUDIT:\n1. Legal gaps (missing filings, expiring SOLs)\n2. Technical gaps (Supabase RLS, GitHub, MCP)\n3. Security vulnerabilities\n4. Integration opportunities\nSeverity + fix + timeline for each. P0/P1/P2.`;
    else if(input==="/daily")               msg=`APEX DAILY BRIEFING — ${d} ${ts} HST:\n1. Case 1FDV-23-0001009 — actions due today/week\n2. SOL countdown status\n3. Technical stack priorities\n4. P0 items\n5. Strategic note for Kekoa`;
    else if(input.startsWith("/analyze ")) msg=`[DEEP ANALYSIS] ${input.slice(9)}\nMulti-dimensional. Patterns, implications, edge cases. Expert precision.`;
    else if(context!=="general")            msg=`[${context.toUpperCase()}] ${input}`;

    const memCtx=Memory.getContext();
    messages.push({role:"user",content:msg});
    try{
      const response=await streamResponse(client,messages,model,memCtx);
      messages.push({role:"assistant",content:response});
      Memory.addFact(`[${d}] ${input.slice(0,80)}`);
      if(messages.length>60)messages=messages.slice(-60);
      Store.save(PATHS.session,{messages,context});
    }catch(e){
      console.log(`\n  ${C.red}✗ ${e.message}${C.reset}\n`);
      if(e.status===401)console.log(`  ${C.gray}Check key: /key sk-ant-...${C.reset}\n`);
      messages.pop();
    }
    sp();
  });

  rl.on("close",()=>{Store.save(PATHS.session,{messages,context});console.log(`\n  ${C.teal}APEX${C.reset} ${C.gray}For Kekoa. Justice never sleeps.${C.reset}\n`);process.exit(0);});
}

main().catch(e=>{console.error(`\x1b[31mFatal: ${e.message}\x1b[0m`);process.exit(1);});
