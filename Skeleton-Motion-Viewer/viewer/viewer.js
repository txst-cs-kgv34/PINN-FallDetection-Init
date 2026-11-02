'use strict';
const $=id=>document.getElementById(id);
const canvas=$('canvas'),ctx=canvas.getContext('2d');
let trials=[],frames=[],frame=0,playing=false,previousTime=null,accumulator=0;
let yaw=-.5,pitch=.18,zoom=1,scene=null,drag=null,loadVersion=0;
const left=new Set([4,5,6,7,8,9,10,18,19,20,21]);
const right=new Set([11,12,13,14,15,16,17,22,23,24,25]);
const color=j=>left.has(j)?'#007d9c':right.has(j)?'#c66128':'#344e5d';
const fps=()=>Math.max(.1,Math.min(1000,Number($('fps').value)||30));
function pause(){playing=false;$('play').textContent='Play';previousTime=null;accumulator=0;}
function toggle(){if(!frames.length)return;if(playing){pause();return;}if(frame===frames.length-1)frame=0;playing=true;$('play').textContent='Pause';previousTime=null;update();}
function selectTrial(){pause();const item=trials[Number($('trial').value)];frames=item?Skeleton.toMeters(item.raw,$('units').value):[];frame=0;scene=frames.length?Skeleton.bounds(frames,$('follow').checked):null;zoom=1;
  for(const id of ['prev','play','next','snapshot','scrubber','frame'])$(id).disabled=!frames.length;
  $('scrubber').max=$('frame').max=Math.max(0,frames.length-1);$('empty').style.display=frames.length?'none':'grid';update();}
function update(){
  if(frames.length){const item=trials[Number($('trial').value)];$('metadata').textContent=`${item.name} · ${frames.length} frames · 32 joints · nominal coverage ${(frames.length/fps()).toFixed(2)} s · first-to-last ${((frames.length-1)/fps()).toFixed(2)} s`;
    $('frame').value=$('scrubber').value=frame;$('position').textContent=`Frame ${frame} of ${frames.length-1} (zero-based) · CSV row ${frame+1} · nominal time ${(frame/fps()).toFixed(3)} s`;
    const step=Skeleton.maxStep(frames,frame);$('jump').textContent=step?`Largest step from previous frame: ${step.distance.toFixed(3)} m · ${Skeleton.names[step.joint]} (joint ${step.joint})`:'First frame: no previous-frame displacement.';
  }draw();
}
function move(index){pause();frame=Math.max(0,Math.min(frames.length-1,Math.round(Number(index)||0)));update();}
function rotate(p){
  // Camera coordinates remain the source. All views are orthographic with equal axes.
  const mode=$('view').value;
  if(mode==='xy')return [p[0],-p[1],p[2]];
  if(mode==='yz')return [p[2],-p[1],p[0]];
  if(mode==='xz')return [p[0],p[2],p[1]];
  const x=Math.cos(yaw)*p[0]+Math.sin(yaw)*p[2];
  const z=-Math.sin(yaw)*p[0]+Math.cos(yaw)*p[2];
  const y=-p[1];return [x,Math.cos(pitch)*y-Math.sin(pitch)*z,Math.sin(pitch)*y+Math.cos(pitch)*z];
}
function draw(){
  const w=canvas.clientWidth,h=canvas.clientHeight,ratio=window.devicePixelRatio||1;
  if(canvas.width!==Math.round(w*ratio)||canvas.height!==Math.round(h*ratio)){canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);}
  ctx.setTransform(ratio,0,0,ratio,0,0);ctx.fillStyle='#ffffff';ctx.fillRect(0,0,w,h);
  if(!frames.length)return;
  const pose=frames[frame],follow=$('follow').checked,s=Math.min(w,h)*.40/scene.radius*zoom;
  function project(p){const q=rotate(p.map((v,k)=>v-(follow?pose[0][k]:0)-scene.center[k]));return [w/2+q[0]*s,h/2-q[1]*s,q[2]];}
  if($('trail').checked&&!follow){ctx.strokeStyle='#a8bfc8';ctx.lineWidth=1.5;ctx.beginPath();for(let i=0;i<=frame;i++){const p=project(frames[i][0]);if(i===0)ctx.moveTo(...p.slice(0,2));else ctx.lineTo(...p.slice(0,2));}ctx.stroke();}
  const points=pose.map(project);
  const sortedEdges=[...Skeleton.edges].sort((a,b)=>(points[a[0]][2]+points[a[1]][2])-(points[b[0]][2]+points[b[1]][2]));
  for(const [a,b] of sortedEdges){
    ctx.strokeStyle=color(b);ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(points[a][0],points[a][1]);ctx.lineTo(points[b][0],points[b][1]);ctx.stroke();
  }
  points.forEach((p,j)=>{ctx.fillStyle=color(j);ctx.beginPath();ctx.arc(p[0],p[1],j===0?5:3,0,Math.PI*2);ctx.fill();if($('labels').checked){ctx.font='11px system-ui';ctx.fillText(String(j),p[0]+5,p[1]-5);}});
  ctx.fillStyle='#365160';ctx.font='13px system-ui';ctx.fillText(`${trials[Number($('trial').value)].name} · frame ${frame} · ${(frame/fps()).toFixed(3)} s`,16,24);
  ctx.fillText('Camera axes · no inferred floor or contact',16,h-16);
  // Camera-axis compass, using exactly the same projection as the skeleton.
  [['X',[1,0,0],'#b64437'],['Y',[0,1,0],'#3a8750'],['Z',[0,0,1],'#3970ac']].forEach(([label,p,c])=>{const q=rotate(p);ctx.strokeStyle=c;ctx.fillStyle=c;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(w-65,h-65);ctx.lineTo(w-65+q[0]*32,h-65-q[1]*32);ctx.stroke();ctx.fillText(label,w-65+q[0]*43,h-65-q[1]*43);});
}
$('files').addEventListener('change',async event=>{
  const version=++loadVersion;pause();const loaded=[],errors=[];
  for(const file of event.target.files){try{if(file.size>50*1024*1024)throw new Error('File exceeds the 50 MiB viewer limit. Split a long recording into clips.');loaded.push({name:file.name,raw:Skeleton.parseCSV(await file.text())});}catch(error){errors.push(`${file.name}: ${error.message}`);}}
  if(version!==loadVersion)return;
  $('error').textContent=errors.join('\n');
  // Preserve the current clip if every new file was rejected.
  if(!loaded.length)return;
  trials=loaded;$('trial').replaceChildren(...trials.map((t,i)=>{const o=document.createElement('option');o.value=i;o.textContent=t.name;return o;}));$('trial').disabled=false;selectTrial();
});
$('trial').onchange=selectTrial;$('units').onchange=selectTrial;
$('fps').onchange=()=>{$('fps').value=fps();pause();update();};
$('play').onclick=toggle;$('prev').onclick=()=>move(frame-1);$('next').onclick=()=>move(frame+1);
$('scrubber').oninput=e=>move(e.target.value);$('frame').onchange=e=>move(e.target.value);
$('view').onchange=draw;$('labels').onchange=draw;$('trail').onchange=draw;
$('follow').onchange=()=>{if(frames.length)scene=Skeleton.bounds(frames,$('follow').checked);$('trail').disabled=$('follow').checked;draw();};
$('reset').onclick=()=>{yaw=-.5;pitch=.18;zoom=1;draw();};
$('snapshot').onclick=()=>{draw();const a=document.createElement('a');a.download=`${trials[Number($('trial').value)].name.replace(/\.csv$/i,'')}_frame_${frame}.png`;a.href=canvas.toDataURL('image/png');a.click();};
canvas.addEventListener('pointerdown',e=>{if($('view').value!=='3d')return;drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointermove',e=>{if(!drag)return;yaw+=(e.clientX-drag[0])*.008;pitch=Math.max(-1.5,Math.min(1.5,pitch+(e.clientY-drag[1])*.008));drag=[e.clientX,e.clientY];draw();});
for(const name of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(name,()=>{drag=null;});
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.25,Math.min(8,zoom*Math.exp(-e.deltaY*.001)));draw();},{passive:false});
document.addEventListener('keydown',e=>{if(['INPUT','SELECT','BUTTON','TEXTAREA'].includes(e.target.tagName)||!frames.length)return;if(e.code==='Space'){e.preventDefault();toggle();}if(e.code==='ArrowLeft'){e.preventDefault();move(frame-1);}if(e.code==='ArrowRight'){e.preventDefault();move(frame+1);}});
new ResizeObserver(draw).observe(canvas);
document.addEventListener('visibilitychange',()=>{previousTime=null;accumulator=0;});
function tick(now){if(playing&&frames.length){if(previousTime!==null){accumulator+=(now-previousTime)/1000*fps()*Number($('speed').value);const count=Math.floor(accumulator);if(count){accumulator-=count;frame+=count;if(frame>=frames.length){if($('loop').checked)frame%=frames.length;else{frame=frames.length-1;pause();}}update();}}previousTime=now;}requestAnimationFrame(tick);}
requestAnimationFrame(tick);draw();
