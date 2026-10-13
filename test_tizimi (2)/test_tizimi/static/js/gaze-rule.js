/* Pure state machine: one continuous excursion = one event, never five frames. */
(function (root) {
  class GazeRule {
    constructor({awayMs=2000, returnMs=1000, maxGapMs=3500}={}) {
      this.awayMs=awayMs;this.returnMs=returnMs;this.maxGapMs=maxGapMs;this.reset();
    }
    reset(){this.awaySince=null;this.returnSince=null;this.latched=false;this.last=null;}
    sample(kind,now){
      if(this.last!==null && now-this.last>this.maxGapMs){this.awaySince=null;this.returnSince=null;}
      this.last=now;
      // Missing/uncertain input breaks continuity, but never rearms a counted excursion.
      if(kind==='unknown'){this.awaySince=null;this.returnSince=null;return false;}
      if(kind==='front'){
        this.awaySince=null;
        if(this.returnSince===null)this.returnSince=now;
        if(now-this.returnSince>=this.returnMs)this.latched=false;
        return false;
      }
      this.returnSince=null;
      if(this.latched)return false;
      if(this.awaySince===null)this.awaySince=now;
      if(now-this.awaySince>=this.awayMs){this.latched=true;return true;}
      return false;
    }
  }
  root.GazeRule=GazeRule;
  if(typeof module!=='undefined')module.exports=GazeRule;
})(typeof self!=='undefined'?self:globalThis);
