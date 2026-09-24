import { useState, type ReactNode, type FormEvent } from 'react';
import { Box, Database, BookOpen, ArrowUpRight, LogOut, ArrowRight } from 'lucide-react';
import { login, type Session } from './api';

const names = ['Stockroom','Import Desk','Source Notes'];
const urls = ['https://jaryn2.github.io/projects/stockroom/','/','https://jaryn2.github.io/projects/source-notes/'];
const icons = [Box,Database,BookOpen];
export function Shell({index,children,user,onLogout}:{index:number;children:ReactNode;user:string;onLogout:()=>void}) {
  const Icon = icons[index];
  return <div className={'app theme-'+index}><aside className="sidebar">
    <a className="brand" href="/"><span className="brand-icon"><Icon size={23}/></span>{names[index]}<span className="brand-dot">.</span></a>
    <div className="workspace-label">JARYN WEINEL / PROJECTS</div>
    <nav aria-label="Projects">{names.map((name,i)=>{const NavIcon=icons[i];return <a key={name} className={index===i?'nav-link active':'nav-link'} href={urls[i]}><NavIcon size={18}/>{name}{index!==i&&<ArrowUpRight size={14}/>}</a>})}</nav>
    <div className="sidebar-note"><span className="live-dot"/>Local workspace<p>Sample records.<br/>Real working apps.</p></div>
    <div className="profile"><span className="avatar">{user[0]?.toUpperCase() || 'J'}</span><div><strong>{user || 'Welcome'}</strong><small>Demo account</small></div>{user&&<button className="icon-button" aria-label="Sign out" onClick={onLogout}><LogOut size={18}/></button>}</div>
  </aside><main><div className="topbar"><span>Portfolio / <b>{names[index]}</b></span><span className="topbar-tag">Practice workspace</span></div>{children}<footer>Built by Jaryn Weinel with coding assistance. Sample data for learning and testing.</footer></main></div>;
}
export function SignIn({index,onLogin}:{index:number;onLogin:(session:Session)=>void}) {
  const [username,setUsername]=useState(index===0?'worker':'demo');
  const [password,setPassword]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const descriptions=['Follow an order from the shelf to the loading bay.','Find the rows that need a second look.','Keep the source close to the answer.'];
  async function submit(event:FormEvent) {event.preventDefault();setBusy(true);setError('');try{onLogin(await login(username,password));}catch(error){setError((error as Error).message);}finally{setBusy(false);}}
  return <Shell index={index} user="" onLogout={()=>{}}><section className="login-layout"><div><span className="eyebrow">A SMALL APP. A COMPLETE WORKFLOW.</span><h1>{descriptions[index]}</h1><p className="lead">{index===0?'Create orders, pick available stock, and keep track of every change.':index===1?'Import fleet records, review rejected rows, and see whether the next update arrived.':'Search a few documents, read the exact passages, and review a note before saving it.'}</p><div className="login-steps"><span>01 &nbsp; Try the sample data</span><span>02 &nbsp; Follow a task through</span><span>03 &nbsp; Check the record</span></div></div><form className="panel login-panel" onSubmit={submit}><span className="eyebrow">YOUR WORKSPACE</span><h2>Sign in to try it</h2><p className="muted">The local password is in <code>.env</code> under <code>DEMO_PASSWORD</code>.</p><label>Account{index===0?<select value={username} onChange={e=>setUsername(e.target.value)}><option value="worker">Worker</option><option value="manager">Manager</option></select>:<input value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username" required/>}</label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password" required/></label>{error&&<p role="alert" className="error">{error}</p>}<button className="primary" disabled={busy}>{busy?'Signing in...':'Open workspace'}<ArrowRight size={17}/></button><p className="tiny">Changes stay in this local demo database.</p></form></section></Shell>;
}
export function Badge({value}:{value:string}) {return <span className={'badge '+value}>{value.replaceAll('_',' ')}</span>;}
export function Stat({label,value,note}:{label:string;value:ReactNode;note:string}) {return <div className="stat"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;}
export function Empty({title,children}:{title:string;children?:ReactNode}) {return <div className="empty"><h3>{title}</h3><p>{children}</p></div>;}
export function Notice({error,message}:{error?:string;message?:string}) {return error?<div role="alert" className="notice error">{error}</div>:message?<div role="status" className="notice success">{message}</div>:null;}
