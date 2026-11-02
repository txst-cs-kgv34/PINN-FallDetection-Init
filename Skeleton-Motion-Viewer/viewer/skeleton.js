/* Pure CSV / geometry helpers, usable in a browser or Node's test runner. */
(function (root) {
  'use strict';
  const names = ['pelvis','spine_navel','spine_chest','neck','clavicle_left','shoulder_left','elbow_left','wrist_left','hand_left','handtip_left','thumb_left','clavicle_right','shoulder_right','elbow_right','wrist_right','hand_right','handtip_right','thumb_right','hip_left','knee_left','ankle_left','foot_left','hip_right','knee_right','ankle_right','foot_right','head','nose','eye_left','ear_left','eye_right','ear_right'];
  const parents = [-1,0,1,2,2,4,5,6,7,8,7,2,11,12,13,14,15,14,0,18,19,20,0,22,23,24,3,26,26,26,26,26];
  const edges = parents.flatMap((p,j) => p < 0 ? [] : [[p,j]]);
  function parseCSV(text) {
    const lines=text.replace(/^\uFEFF/,'').split(/\r?\n/);
    while(lines.length && !lines[lines.length-1].trim()) lines.pop();
    if(!lines.length) throw new Error('The CSV is empty.');
    return lines.map((line,i) => {
      const cells=line.split(',');
      if(cells.length!==96) throw new Error(`Line ${i+1}: expected 96 columns, found ${cells.length}. Use headerless 32-joint xyz data.`);
      const values=cells.map((cell,j) => {
        const value=cell.trim();
        // Decimal/scientific notation only; do not silently accept blanks or hex.
        if(!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(value) || !Number.isFinite(Number(value)))
          throw new Error(`Line ${i+1}, column ${j+1}: expected a finite numeric coordinate.`);
        return Number(value);
      });
      return Array.from({length:32},(_,j)=>values.slice(j*3,j*3+3));
    });
  }
  function toMeters(frames,units) {
    const scale=units==='mm' ? .001 : 1;
    return frames.map(frame=>frame.map(p=>p.map(v=>v*scale)));
  }
  function bounds(frames,follow) {
    const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
    for(const frame of frames) for(const p of frame) for(let k=0;k<3;k++) {
      const v=p[k]-(follow?frame[0][k]:0);lo[k]=Math.min(lo[k],v);hi[k]=Math.max(hi[k],v);
    }
    return {center:lo.map((v,k)=>(v+hi[k])/2),radius:Math.max(.1,Math.hypot(...hi.map((v,k)=>v-lo[k]))/2)};
  }
  function maxStep(frames,i) {
    if(i===0) return null;
    let distance=0,joint=0;
    frames[i].forEach((p,j)=>{const d=Math.hypot(...p.map((v,k)=>v-frames[i-1][j][k]));if(d>distance){distance=d;joint=j;}});
    return {distance,joint};
  }
  const api={names,edges,parseCSV,toMeters,bounds,maxStep};
  if(typeof module!=='undefined' && module.exports) module.exports=api;
  else root.Skeleton=api;
})(typeof globalThis==='undefined'?this:globalThis);
