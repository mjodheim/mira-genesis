import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const RESPONSE_SCHEMA = 'm048-node-response-v1';

function header(name, meta) {
  return `// M048_META ${JSON.stringify({module:name,...meta}, Object.keys({module:name,...meta}).sort())}\n`;
}

function renderInterpretation(aliases) {
  const ordered = Object.fromEntries(Object.entries(aliases).sort(([a],[b])=>a.localeCompare(b)));
  return header('interpretation',{kind:'recursive_prefix_parser',aliases:ordered})+
    `export const ALIASES=${JSON.stringify(ordered)};\n`+
    `export const ARITIES={"add":2,"max":2,"mean":3,"mul":2};\n`+
    `function number(token){const value=Number(token);return Number.isFinite(value)?value:null;}\n`+
    `function parse(tokens,index){if(index>=tokens.length)throw new Error('unexpected_end');const token=tokens[index].toLowerCase();const value=number(token);if(value!==null)return [{kind:'number',value},index+1];const canonical=ALIASES[token];if(!canonical)throw new Error('unknown_operator:'+token);const args=[];let cursor=index+1;for(let i=0;i<ARITIES[canonical];i++){const parsed=parse(tokens,cursor);args.push(parsed[0]);cursor=parsed[1];}return [{kind:'call',op:canonical,args},cursor];}\n`+
    `export function interpret(text){const tokens=text.trim().split(/\\s+/).filter(Boolean);if(!tokens.length)throw new Error('empty_request');const [node,cursor]=parse(tokens,0);if(cursor!==tokens.length)throw new Error('trailing_tokens');return node;}\n`;
}

function renderSelection(routes) {
  const ordered = Object.fromEntries(Object.entries(routes).sort(([a],[b])=>a.localeCompare(b)));
  return header('selection',{kind:'route_table',routes:ordered})+
    `export const ROUTES=${JSON.stringify(ordered)};\n`+
    `export function select(step){const route=ROUTES[step.op];if(!route)throw new Error('route_missing:'+step.op);return route;}\n`;
}

function renderTool(name, expression) {
  let body;
  if (expression === 'maximum') body = 'return Math.max(...args);';
  else if (expression === 'minimum') body = 'return Math.min(...args);';
  else if (expression === 'sum') body = 'return args.reduce((a,b)=>a+b,0);';
  else if (expression === 'midpoint') body = 'return (args[0]+args[args.length-1])/2;';
  else throw new Error('unsupported_tool_expression:'+expression);
  return header(`tool_${name}`,{kind:'synthesized_tool',tool_name:name,expression_id:expression})+
    `export function ${name}(args){if(!args.length)throw new Error('tool_requires_arguments');${body}}\n`+
    `export const TOOLS={${name}};\n`;
}

function clone(value) { return JSON.parse(JSON.stringify(value)); }

function moduleMap(body) {
  return Object.fromEntries(body.modules.map(module=>[module.name,module]));
}

function replaceModules(body, replacements, addedCases=[]) {
  const byName = moduleMap(body);
  for (const [name,module] of Object.entries(replacements)) byName[name] = module;
  const existing = new Set(body.regression_cases.map(item=>item.case_id));
  const regression = [...body.regression_cases];
  for (const item of addedCases) if (!existing.has(item.case_id)) { regression.push(item); existing.add(item.case_id); }
  return {schema:'m048-js-body-v1',modules:Object.values(byName).sort((a,b)=>a.name.localeCompare(b.name)),regression_cases:regression};
}

async function loadBody(body) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(),'m048-node-body-'));
  const modules = {};
  const tools = {};
  try {
    for (const item of body.modules) await fs.writeFile(path.join(directory,`${item.name}.mjs`),item.source,'utf8');
    for (const item of body.modules) {
      const url = pathToFileURL(path.join(directory,`${item.name}.mjs`));
      url.searchParams.set('identity',`${process.pid}-${Date.now()}-${item.name}`);
      modules[item.name] = await import(url.href);
    }
    for (const [name,module] of Object.entries(modules)) {
      if (name === 'tool_core' || name.startsWith('tool_')) {
        if (!module.TOOLS || typeof module.TOOLS !== 'object') throw new Error(`tool_registry_missing:${name}`);
        for (const [toolName,tool] of Object.entries(module.TOOLS)) {
          if (toolName in tools) throw new Error(`duplicate_tool:${toolName}`);
          if (typeof tool !== 'function') throw new Error(`invalid_tool:${toolName}`);
          tools[toolName] = tool;
        }
      }
    }
    return {directory,modules,tools};
  } catch (error) {
    await fs.rm(directory,{recursive:true,force:true});
    throw error;
  }
}

async function executeBody(body,cases) {
  const loaded = await loadBody(body);
  try {
    const results = [];
    for (const item of cases) {
      const result = loaded.modules.orchestration.run(item.request,loaded.modules,loaded.tools);
      results.push({case_id:item.case_id,request:item.request,expected:item.expected,passed:Boolean(result.ok && result.output === item.expected),result});
    }
    return {runtime:'node-esm',worker_pid:process.pid,module_count:body.modules.length,regression_case_count:body.regression_cases.length,all_passed:results.every(item=>item.passed),case_results:results};
  } finally {
    await fs.rm(loaded.directory,{recursive:true,force:true});
  }
}

function publicGeneratedCases(taskId,cases) {
  return cases.map((item,index)=>({case_id:`case_${taskId}_${index+1}`,request:item.request,expected:item.expected,origin:taskId}));
}

function changedModules(parent,candidate) {
  const before = moduleMap(parent); const after = moduleMap(candidate);
  return Object.keys({...before,...after}).filter(name=>!before[name] || !after[name] || before[name].source !== after[name].source).sort();
}

function sourceBytes(body) {
  return body.modules.reduce((total,item)=>total+Buffer.byteLength(item.source,'utf8'),0)+Buffer.byteLength(JSON.stringify(body.regression_cases),'utf8');
}

function unknownToken(execution) {
  const failures = execution.case_results.filter(item=>!item.passed);
  const tokens = new Set();
  for (const failure of failures) {
    const message = String(failure.result.error_message ?? '');
    if (failure.result.error_stage === 'interpretation' && message.startsWith('unknown_operator:')) tokens.add(message.slice('unknown_operator:'.length));
  }
  return tokens.size === 1 ? [...tokens][0] : null;
}

async function propose(request) {
  const {body,task_id,public_cases,max_generated_candidates,max_candidate_bytes} = request;
  const incumbent = await executeBody(body,public_cases);
  const token = unknownToken(incumbent);
  if (!token) return {status:'insufficient_diagnosis',diagnosed_module:null,generated_candidates:0,complete_program_space_enumerated:false,candidates:[],incumbent};
  const byName = moduleMap(body);
  const aliases = {...byName.interpretation.meta.aliases};
  const routes = {...byName.selection.meta.routes};
  const generatedCases = publicGeneratedCases(task_id,public_cases);
  const candidates = [];
  function addCandidate(templateId,replacements) {
    if (candidates.length >= max_generated_candidates) return;
    const candidateBody = replaceModules(body,replacements,generatedCases);
    if (sourceBytes(candidateBody) > max_candidate_bytes) return;
    candidates.push({template_id:templateId,diagnosed_module:'interpretation',changed_modules:changedModules(body,candidateBody),added_modules:changedModules(body,candidateBody).filter(name=>!(name in byName)),candidate_body:candidateBody});
  }
  if (token === 'maximum') {
    for (const expression of ['maximum','minimum','sum','midpoint']) {
      const nextAliases = {...aliases,[token]:'max'};
      const nextRoutes = {...routes,max:'max'};
      addCandidate(`native_composite_max_${expression}`,{
        interpretation:{name:'interpretation',source:renderInterpretation(nextAliases),meta:{kind:'recursive_prefix_parser',aliases:Object.fromEntries(Object.entries(nextAliases).sort())}},
        selection:{name:'selection',source:renderSelection(nextRoutes),meta:{kind:'route_table',routes:Object.fromEntries(Object.entries(nextRoutes).sort())}},
        tool_max:{name:'tool_max',source:renderTool('max',expression),meta:{kind:'synthesized_tool',tool_name:'max',expression_id:expression}},
      });
    }
  } else if (token === 'largest' && 'tool_max' in byName) {
    const nextAliases = {...aliases,[token]:'max'};
    addCandidate('native_alias_reuse_max',{
      interpretation:{name:'interpretation',source:renderInterpretation(nextAliases),meta:{kind:'recursive_prefix_parser',aliases:Object.fromEntries(Object.entries(nextAliases).sort())}},
    });
  } else if (token === 'median') {
    for (const canonical of ['mean','max','add']) {
      const nextAliases = {...aliases,[token]:canonical};
      addCandidate(`native_alias_median_${canonical}`,{
        interpretation:{name:'interpretation',source:renderInterpretation(nextAliases),meta:{kind:'recursive_prefix_parser',aliases:Object.fromEntries(Object.entries(nextAliases).sort())}},
      });
    }
  }
  const scored = [];
  for (const candidate of candidates) {
    const execution = await executeBody(candidate.candidate_body,public_cases);
    scored.push({...candidate,public_passes:execution.case_results.filter(item=>item.passed).length,public_total:public_cases.length});
  }
  scored.sort((a,b)=>b.public_passes-a.public_passes || a.template_id.localeCompare(b.template_id));
  return {status:scored.length?'ready':'insufficient_evidence',diagnosed_module:'interpretation',unknown_token:token,generated_candidates:scored.length,program_space_lower_bound:65536,complete_program_space_enumerated:false,candidates:scored,incumbent};
}

async function validate(request) {
  const {parent_body,proposal,retained_cases,public_cases,hidden_cases,expected_changed_modules,max_validation_attempts} = request;
  const complete = [...retained_cases,...public_cases,...hidden_cases];
  const incumbent = await executeBody(parent_body,complete);
  const attempts = [];
  const expected = [...expected_changed_modules].sort().join(',');
  for (const candidate of proposal.candidates.slice(0,max_validation_attempts)) {
    const execution = await executeBody(candidate.candidate_body,complete);
    const changed = [...candidate.changed_modules].sort().join(',');
    const retainedIds = new Set(retained_cases.map(item=>item.case_id));
    const publicIds = new Set(public_cases.map(item=>item.case_id));
    const hiddenIds = new Set(hidden_cases.map(item=>item.case_id));
    const retainedPassed = execution.case_results.filter(item=>retainedIds.has(item.case_id)&&item.passed).length;
    const publicPassed = execution.case_results.filter(item=>publicIds.has(item.case_id)&&item.passed).length;
    const hiddenPassed = execution.case_results.filter(item=>hiddenIds.has(item.case_id)&&item.passed).length;
    const accepted = changed===expected && retainedPassed===retainedIds.size && publicPassed===publicIds.size && hiddenPassed===hiddenIds.size;
    attempts.push({template_id:candidate.template_id,changed_modules:candidate.changed_modules,retained_passed:retainedPassed,retained_total:retainedIds.size,public_passed:publicPassed,public_total:publicIds.size,hidden_passed:hiddenPassed,hidden_total:hiddenIds.size,accepted});
    if (accepted) return {action:'adopt',reason:'candidate passed retained, public and hidden native suites',selected_candidate:candidate,attempts,incumbent_task_passes:incumbent.case_results.filter(item=>(publicIds.has(item.case_id)||hiddenIds.has(item.case_id))&&item.passed).length,worker_pid:process.pid};
  }
  return {action:'terminate_insufficient_evidence',reason:'no native candidate earned independent release authority',selected_candidate:null,attempts,worker_pid:process.pid};
}

async function main() {
  const mode = process.argv[2];
  try {
    const chunks=[]; for await (const chunk of process.stdin) chunks.push(chunk);
    const request=JSON.parse(Buffer.concat(chunks).toString('utf8'));
    let result;
    if (mode==='execute') result=await executeBody(request.body,request.cases);
    else if (mode==='propose') result=await propose(request);
    else if (mode==='validate') result=await validate(request);
    else throw new Error(`unsupported_mode:${mode}`);
    process.stdout.write(JSON.stringify({schema:RESPONSE_SCHEMA,mode,result}));
  } catch (error) {
    process.stdout.write(JSON.stringify({schema:RESPONSE_SCHEMA,mode,fatal_error:`${error.name}:${error.message}`}));
    process.exitCode=1;
  }
}

await main();
