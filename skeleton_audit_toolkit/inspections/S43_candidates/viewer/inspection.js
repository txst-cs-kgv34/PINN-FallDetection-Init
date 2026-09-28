"use strict";
// The prepared data are embedded in INSPECT.html: no network or server is used.
const data = JSON.parse(document.getElementById("data").textContent);
const ui = Object.fromEntries(["trial","mode","view","speed","frame","time","play","status","traceAxis","filterInfo","notes"].map(id => [id, document.getElementById(id)]));
const colors = {raw:"#176d8a", filtered:"#d07326"};
let index = 0;
let playing = false;
let startedAt = 0;
let startedFrame = 0;
let bounds;
let notes = [];
const currentTrial = () => data.trials[Number(ui.trial.value)];
const currentModes = () => ui.mode.value === "overlay" ? ["raw","filtered"] : [ui.mode.value];
const projection = p => ui.view.value === "xy" ? [p[0],-p[1]] : ui.view.value === "xz" ? [p[0],p[2]] : [p[2],-p[1]];

function setBounds() {
    const trial = currentTrial();
    const origin = trial.modes.raw.pose[0][0];
    const low = [Infinity,Infinity], high = [-Infinity,-Infinity];
    for (const mode of Object.values(trial.modes)) {
        for (const frame of mode.pose) for (const point of frame) {
            const p = projection(point.map((v,i) => v-origin[i]));
            p.forEach((v,i) => {low[i]=Math.min(low[i],v);high[i]=Math.max(high[i],v);});
        }
    }
    bounds = {origin, center:low.map((v,i)=>(v+high[i])/2), span:Math.max(high[0]-low[0],high[1]-low[1],.1)*1.15};
}

function drawPose() {
    const canvas=document.getElementById("pose"),ctx=canvas.getContext("2d");
    const w=canvas.width,h=canvas.height,scale=(Math.min(w,h)-100)/bounds.span;
    const transform=point=>{
        const p=projection(point.map((v,i)=>v-bounds.origin[i]));
        return [w/2+(p[0]-bounds.center[0])*scale,h/2-(p[1]-bounds.center[1])*scale];
    };
    ctx.clearRect(0,0,w,h);ctx.fillStyle="#607783";ctx.font="15px system-ui";
    const labels=ui.view.value==="xy"?["Camera X (m)","Camera −Y (m)"]:ui.view.value==="xz"?["Camera X (m)","Camera Z (m)"]:["Camera Z (m)","Camera −Y (m)"];
    for(let k=-2;k<=2;k++){
        const p=k*bounds.span/5;
        ctx.strokeStyle="#e5ecf0";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(w/2+p*scale,35);ctx.lineTo(w/2+p*scale,h-40);ctx.stroke();
        ctx.beginPath();ctx.moveTo(40,h/2-p*scale);ctx.lineTo(w-30,h/2-p*scale);ctx.stroke();
        ctx.fillText((bounds.center[0]+p).toFixed(2),w/2+p*scale-16,h-22);
        ctx.fillText((bounds.center[1]+p).toFixed(2),8,h/2-p*scale);
    }
    ctx.fillText(labels[0],w/2-60,h-2);ctx.fillText(labels[1],45,20);
    for(const name of currentModes()){
        const mode=currentTrial().modes[name];if(!mode)continue;
        const pose=mode.pose[index];ctx.strokeStyle=colors[name];ctx.lineWidth=name==="raw"?2.5:2;
        ctx.setLineDash(name==="filtered"?[6,3]:[]);
        data.parents.forEach((parent,j)=>{
            if(parent<0)return;const a=transform(pose[parent]),b=transform(pose[j]);
            ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();
        });
        ctx.setLineDash([2,5]);ctx.strokeStyle="#995da0";
        ctx.beginPath();ctx.moveTo(...transform(pose[21]));ctx.lineTo(...transform(pose[25]));ctx.stroke();ctx.setLineDash([]);
        for(const [point,color,radius] of [[mode.com[index],"#14804a",6],[mode.foot_midpoint[index],"#995da0",4]]){
            ctx.beginPath();ctx.fillStyle=color;ctx.arc(...transform(point),radius,0,Math.PI*2);ctx.fill();
        }
    }
}

function drawTrace(id,values) {
    const canvas=document.getElementById(id),ctx=canvas.getContext("2d");
    const trial=currentTrial(),w=canvas.width,h=canvas.height,pad=48;
    const series=Object.entries(trial.modes).map(([name,mode])=>[name,values(mode)]);
    let low=Infinity,high=-Infinity;
    for(const [,arr] of series)for(const v of arr){low=Math.min(low,v);high=Math.max(high,v);}
    const extra=Math.max((high-low)*.12,.01);low-=extra;high+=extra;
    const x=f=>pad+(w-pad*2)*f/(trial.frames-1),y=v=>h-pad-(h-pad*2)*(v-low)/(high-low);
    ctx.clearRect(0,0,w,h);
    ctx.fillStyle="#f8e6e1";
    trial.raw_review_flags.forEach((flag,f)=>{if(flag)ctx.fillRect(x(f)-1,pad,2,h-2*pad);});
    ctx.font="14px system-ui";ctx.fillStyle="#607783";
    for(let i=0;i<=4;i++){
        const v=low+(high-low)*i/4;ctx.strokeStyle="#dce5e9";ctx.lineWidth=1;
        ctx.beginPath();ctx.moveTo(pad,y(v));ctx.lineTo(w-pad,y(v));ctx.stroke();ctx.fillText(v.toFixed(2),2,y(v)+4);
        const f=(trial.frames-1)*i/4;ctx.fillText((f/data.fps).toFixed(1),x(f)-10,h-20);
    }
    for(const [name,arr] of series){
        if(!currentModes().includes(name))continue;
        ctx.strokeStyle=colors[name];ctx.lineWidth=2;ctx.setLineDash(name==="filtered"?[6,3]:[]);ctx.beginPath();
        arr.forEach((v,f)=>f?ctx.lineTo(x(f),y(v)):ctx.moveTo(x(f),y(v)));ctx.stroke();
    }
    ctx.setLineDash([]);ctx.strokeStyle="#253e4c";ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(x(index),pad);ctx.lineTo(x(index),h-pad);ctx.stroke();
    ctx.fillStyle="#607783";ctx.fillText("m",8,22);ctx.fillText("Nominal seconds",w/2-55,h-1);
}

function render() {
    const trial=currentTrial();ui.frame.value=String(index);
    ui.time.textContent=`Frame ${index} / ${trial.frames-1} · ${(index/data.fps).toFixed(3)} s`;
    const flags=[];
    if(trial.raw_review_flags[index])flags.push("RAW REVIEW FLAG");
    if(trial.raw_repeated_previous[index])flags.push("RAW POSE REPEATS PREVIOUS FRAME");
    ui.status.textContent=flags.join(" · ") || "No raw review flag at this frame; this is not a validity guarantee.";
    ui.status.style.background=flags.length?"#f8e6df":"#e0eaf0";
    drawPose();drawTrace("separation",mode=>mode.foot_separation_camera_xz);
    const axis=Number(ui.traceAxis.value);
    drawTrace("relative",mode=>mode.com_relative_to_foot_midpoint.map(p=>p[axis]*(axis===1?-1:1)));
}

function stop() {playing=false;ui.play.textContent="Play";}
function selectTrial() {
    stop();index=0;const trial=currentTrial();ui.frame.max=String(trial.frames-1);
    const hasFiltered=Boolean(trial.modes.filtered);
    Array.from(ui.mode.options).forEach(option=>{option.disabled=option.value!=="raw"&&!hasFiltered;});
    if(!hasFiltered)ui.mode.value="raw";
    ui.filterInfo.textContent=hasFiltered?`Optional comparison: ${trial.filter.cutoff_hz} Hz Butterworth, order ${trial.filter.order_per_pass} per pass, forward-backward. Cutoff is not validated for fall dynamics.`:`Filtered view unavailable: ${trial.filter.status}.`;
    setBounds();render();
}
function tick(now) {
    if(!playing)return;
    index=Math.min(currentTrial().frames-1,startedFrame+Math.floor((now-startedAt)*data.fps*Number(ui.speed.value)/1000));render();
    if(index===currentTrial().frames-1)stop();else requestAnimationFrame(tick);
}

for(const [i,trial] of data.trials.entries())ui.trial.add(new Option(trial.trial,String(i)));
document.getElementById("title").textContent=`${data.subject.subject_id} · Candidate recording inspection`;
document.getElementById("context").textContent=`${data.trials.length} candidate trials · ${data.subject.sex} CoM model · nominal ${data.fps} FPS · ${data.subject.mass_lb} lb · ${data.subject.height_in} in. Excluded: ${Object.keys(data.selection.excluded_trials||{}).join(", ")||"none"}.`;
ui.trial.addEventListener("change",selectTrial);
ui.view.addEventListener("change",()=>{setBounds();render();});
ui.mode.addEventListener("change",render);ui.traceAxis.addEventListener("change",render);
ui.frame.addEventListener("input",()=>{stop();index=Number(ui.frame.value);render();});
ui.speed.addEventListener("change",()=>{startedAt=performance.now();startedFrame=index;});
ui.play.addEventListener("click",()=>{
    if(playing){stop();return;}
    if(index===currentTrial().frames-1)index=0;
    playing=true;startedAt=performance.now();startedFrame=index;ui.play.textContent="Pause";requestAnimationFrame(tick);
});
document.getElementById("previous").addEventListener("click",()=>{stop();index=Math.max(0,index-1);render();});
document.getElementById("next").addEventListener("click",()=>{stop();index=Math.min(currentTrial().frames-1,index+1);render();});
document.getElementById("nextFlag").addEventListener("click",()=>{
    stop();const flags=currentTrial().raw_review_flags;
    let found=flags.findIndex((flag,f)=>flag&&f>index);if(found<0)found=flags.indexOf(true);if(found>=0)index=found;render();
});
document.getElementById("mark").addEventListener("click",()=>{
    notes.push({trial:currentTrial().trial,frame0:index,nominal_time_s:index/data.fps,view_mode:ui.mode.value,
        phase:document.getElementById("phase").value,note:document.getElementById("note").value,status:"manual_provisional_skeleton_observation"});
    ui.notes.textContent=JSON.stringify(notes,null,2);
});
document.getElementById("clearNotes").addEventListener("click",()=>{notes=[];ui.notes.textContent="No phase notes recorded.";});
document.getElementById("exportNotes").addEventListener("click",()=>{
    const blob=new Blob([JSON.stringify({subject:data.subject.subject_id,nominal_fps:data.fps,notes},null,2)],{type:"application/json"});
    const url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=data.subject.subject_id+"_phase_notes.json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
selectTrial();
