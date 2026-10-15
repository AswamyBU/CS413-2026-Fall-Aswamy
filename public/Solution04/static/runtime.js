/* Browser port of backend.py and lambda1.py. No eval or Python execution. */
(function installRuntime(root) {
'use strict';
const schema = {D0Eint:['int'],D0Ebtf:['bool'],D0Evar:['str'],D0Eop1:['str','expr'],D0Eop2:['str','expr','expr'],D0Elam:['str','expr'],D0Efix:['str','str','expr'],D0Eapp:['expr','expr'],D0Eif0:['expr','expr','expr'],D0Elet:['str','expr','expr'],D0Epair:['expr','expr'],D0Epfst:['expr'],D0Epsnd:['expr']};
function read(source) {
 if (!source.trim() || new TextEncoder().encode(source).length>65536) throw Error('Source must contain 1–65,536 UTF-8 bytes.');
 let pos=0;
 function skip(){while(pos<source.length){if(/\s/.test(source[pos]))pos++;else if(source[pos]==='#'){while(pos<source.length&&source[pos]!=='\n')pos++;}else break;}}
 function take(c){skip();if(source[pos++]!==c)throw Error(`Expected ${c} at character ${pos}.`);}
 function parse(type='expr') {
  skip();
  if(type==='str') {
   const quote=source[pos++];if(quote!=="'"&&quote!=='"')throw Error('Expected a literal string.');
   let value='';
   while(pos<source.length){let c=source[pos++];if(c===quote)return value;if(c==='\n'||c==='\r')throw Error('Unterminated string.');if(c==='\\'){c=source[pos++];const escapes={n:'\n',r:'\r',t:'\t',b:'\b',f:'\f',v:'\v',a:'\x07','\\':'\\',"'":"'",'"':'"'};if(c in escapes)c=escapes[c];else if(['x','u','U'].includes(c)){const n={x:2,u:4,U:8}[c],hex=source.slice(pos,pos+n);if(!new RegExp(`^[0-9a-fA-F]{${n}}$`).test(hex))throw Error('Invalid string escape.');c=String.fromCodePoint(parseInt(hex,16));pos+=n;}else if(c==='\n')c='';else c='\\'+c;}value+=c;}
   throw Error('Unterminated string.');
  }
  if(type==='int'){const match=source.slice(pos).match(/^-?\s*(?:0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|[0-9][0-9_]*)/);if(!match)throw Error('Expected a literal integer.');pos+=match[0].length;let s=match[0].replace(/[\s_]/g,'');return s.startsWith('-')?-BigInt(s.slice(1)):BigInt(s);}
  if(type==='bool'){const match=source.slice(pos).match(/^(True|False)\b/);if(!match)throw Error('Expected True or False.');pos+=match[0].length;return match[0]==='True';}
  if(source[pos]==='('){pos++;const v=parse();take(')');return v;}
  const match=source.slice(pos).match(/^D0E\w+/), name=match&&match[0];if(!Object.hasOwn(schema,name))throw Error('Use only supported D0E constructor calls; Python code is not allowed.');pos+=name.length;take('(');const args=schema[name].map((t,i)=>{if(i)take(',');return parse(t);});skip();if(source[pos]===',')pos++;take(')');return {tag:name,args};
 }
 const expr=parse();skip();if(pos!==source.length)throw Error(`Unexpected input at character ${pos+1}.`);return expr;
}
function free(expr,bound=new Set(),out=new Set()) {
 const [a,b,c]=expr.args;
 const bind=(...names)=>new Set([...bound,...names]);
 switch(expr.tag){
 case 'D0Evar':if(!bound.has(a))out.add(a);break;
 case 'D0Elam':free(b,bind(a),out);break;
 case 'D0Efix':free(c,bind(a,b),out);break;
 case 'D0Elet':free(b,bound,out);free(c,bind(a),out);break;
 default:for(const arg of expr.args)if(arg&&arg.tag)free(arg,bound,out);
 }return out;
}
const val=(tag,...args)=>({tag,args});
function repr(v) {
 if (typeof v==='bigint') return String(v);
 if (typeof v==='boolean') return v?'True':'False';
 if (typeof v==='string') {
  const quote=v.includes("'")&&!v.includes('"')?'"':"'";
  return quote+[...v].map(c=>c===quote?'\\'+c:c==='\\'?'\\\\':c==='\n'?'\\n':c==='\r'?'\\r':c==='\t'?'\\t':c.codePointAt(0)<32?'\\x'+c.codePointAt(0).toString(16).padStart(2,'0'):c).join('')+quote;
 }
 if (v===null) return 'ENVnil()';
 const named=v.tag==='D0Eop1'||v.tag==='D0Eop2';
 return `${v.tag}(${v.args.map((a,i)=>`${named?(i===0?'name':`arg${i}`):`arg${i+1}`}=${repr(a)}`).join(', ')})`;
}

function evaluate(expr,env=null) {
 const [a,b,c]=expr.args, ev=e=>evaluate(e,env), check=(v,t)=>{if(v.tag!==t)throw TypeError(`${t}(...) expected: ${repr(v)}`);return v.args[0];};
 switch(expr.tag){
 case 'D0Eint':return val('D0Vint',a);
 case 'D0Ebtf':return val('D0Vbtf',a);
 case 'D0Evar':for(let e=env;e;e=e.args[2])if(e.args[0]===a)return e.args[1];return val('D0V000');
 case 'D0Elam':return val('D0Vlam',env,expr);
 case 'D0Efix':return val('D0Vfix',env,expr);
 case 'D0Elet':return evaluate(c,val('ENVcns',a,ev(b),env));
 case 'D0Eif0':return ev(check(ev(a),'D0Vbtf')?b:c);
 case 'D0Epair':return val('D0Vpair',ev(a),ev(b));
 case 'D0Epfst':case 'D0Epsnd':{const p=ev(a);check(p,'D0Vpair');return p.args[expr.tag==='D0Epfst'?0:1];}
 case 'D0Eapp':{const fn=ev(a),arg=ev(b);if(fn.tag==='D0Vlam'){const [x,body]=fn.args[1].args;return evaluate(body,val('ENVcns',x,arg,fn.args[0]));}if(fn.tag==='D0Vfix'){const [f,x,body]=fn.args[1].args;return evaluate(body,val('ENVcns',x,arg,val('ENVcns',f,fn,fn.args[0])));}throw TypeError('Application requires D0Vlam/D0Vfix.');}
 case 'D0Eop1':{const x=check(ev(b),'D0Vint');if(a==='+1')return val('D0Vint',x+1n);if(a==='-1')return val('D0Vint',x-1n);throw TypeError('Unsupported unary operator: '+a);}
 case 'D0Eop2':{const left=ev(b),right=ev(c),x=check(left,'D0Vint'),y=check(right,'D0Vint');switch(a){
 case '+':return val('D0Vint',x+y);case '-':return val('D0Vint',x-y);case '*':return val('D0Vint',x*y);
 case '/':if(y===0n)throw Error('integer division by zero');return val('D0Vint',x/y-((x%y!==0n&&(x<0n)!==(y<0n))?1n:0n));
 case '<':return val('D0Vbtf',x<y);case '>':return val('D0Vbtf',x>y);case '<=':return val('D0Vbtf',x<=y);case '>=':return val('D0Vbtf',x>=y);case '==':return val('D0Vbtf',x===y);case '!=':return val('D0Vbtf',x!==y);default:throw TypeError('Unsupported binary operator: '+a);}}
 default:throw TypeError('Unsupported expression.');
 }
}
function perform(operation,source){
 if(['typecheck','compile'].includes(operation))return {outcome:'not_implemented',text:operation==='compile'?'Compilation is not yet implemented.':'Type checking is not yet implemented.'};
 let expr;try{expr=read(source);}catch(e){return {outcome:'input_error',text:e.message};}
 try{if(operation==='lint'){const names=[...free(expr)].sort();return {outcome:names.length?'language_error':'success',text:names.length?'Undeclared variables: '+names.join(', '):'No free variables found. The program is closed.'};}
 if(operation!=='interpret')throw Error('Unknown operation.');const v=evaluate(expr);const invalid=v=>v.tag==='D0V000'||v.tag==='D0Vpair'&&v.args.some(invalid);if(invalid(v))throw Error('Evaluation returned an undefined value (D0V000); check undeclared variables.');return {outcome:'success',text:repr(v)};
 }catch(e){return {outcome:'runtime_error',text:`${e.name}: ${e.message}`};}
}
root.LambdaRuntime={read,free,evaluate,repr,perform};
// A self-contained worker avoids file:// imports and works offline.
root.LambdaWorkerSource = `(${installRuntime.toString()})(globalThis);\nself.onmessage = ({data}) => self.postMessage(LambdaRuntime.perform(data.operation, data.source));`;
})(globalThis);
