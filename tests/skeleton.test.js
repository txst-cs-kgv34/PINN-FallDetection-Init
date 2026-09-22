const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const S=require('../viewer/skeleton.js');
const file=path.join(__dirname,'../s06_audit/raw/S06A08T03.csv');
test('Real T03 data preserves every frame and reproduces the audited discontinuity',()=>{
  const frames=S.toMeters(S.parseCSV(fs.readFileSync(file,'utf8')),'mm');
  assert.equal(frames.length,195);assert.equal(frames[0].length,32);
  const step=S.maxStep(frames,68);assert.equal(step.joint,21);
  assert.ok(Math.abs(step.distance-.976827964)<1e-8);
});
test('Units do not alter the underlying input and centering preserves dimensions',()=>{
  const raw=S.parseCSV(fs.readFileSync(file,'utf8'));const copy=JSON.stringify(raw);
  const mm=S.toMeters(raw,'mm'),m=S.toMeters(raw,'m');
  assert.ok(Math.abs(mm[0][0][0]*1000-m[0][0][0])<1e-8);assert.equal(JSON.stringify(raw),copy);
  const one=[mm[0]],a=S.bounds(one,false),b=S.bounds(one,true);assert.ok(Math.abs(a.radius-b.radius)<1e-10);
});
test('Malformed rows fail rather than silently shifting joint coordinates',()=>{
  const row=Array(96).fill('1').join(',');
  for(const bad of ['',row+',1',row.replace(/^1,/,','),row.replace(/^1,/, 'NaN,'),row.replace(/^1,/, 'Infinity,'),row+'\n\n'+row])assert.throws(()=>S.parseCSV(bad));
  assert.equal(S.parseCSV('\uFEFF'+row+'\r\n').length,1);
  assert.equal(S.parseCSV(row.replace(/^1,/, '-1.23e+2,'))[0][0][0],-123);
});
