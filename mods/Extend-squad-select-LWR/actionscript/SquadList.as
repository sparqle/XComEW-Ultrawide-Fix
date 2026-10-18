class SquadList extends Panel
{
   var _parent;
   var _y;
   var help_display0;
   var help_display1;
   var help_icon0;
   var help_icon1;
   var unitBoxes;
   static var MAX_UNITS = 12;
   var currentSelection = -1;
   function SquadList()
   {
      super();
      this.anchor = Environment.ANCHOR_BOTTOM_CENTER;
   }
   function onLoad()
   {
      this.unitBoxes = new Array();
      var _loc3_ = 0;
      while(_loc3_ < SquadList.MAX_UNITS)
      {
         this.unitBoxes.push(Bind.movie(this,"SS UnitBox","unit" + _loc3_,{_x:(SquadList.MAX_UNITS / 2 - 1 - _loc3_) * 181}));
         _loc3_ = _loc3_ + 1;
      }
      super.onLoad();
      this.UpdateAnchoring();
      Environment.instance().SubscribeToResolutionUpdate(mx.utils.Delegate.create(this,this.UpdateAnchoring));
   }
   function UpdateAnchoring()
   {
      this.setAnchor(this.anchor);
      this._y -= 25;
   }
   function OnChildMouseEvent(target, event)
   {
      if(event == Input.MOUSE_UP)
      {
         flash.external.ExternalInterface.call("FlashRaiseMouseEvent",String(this),event,String(target));
      }
   }
   function onInput(code, action)
   {
      if(!_global.debugging)
      {
         return false;
      }
      var _loc3_ = true;
      switch(code)
      {
         case Input.DPAD_LEFT:
         case Input.DPAD_RIGHT:
            break;
         default:
            _loc3_ = false;
      }
      return _loc3_;
   }
   function SetUnitInfo(index, status, unitName, nickname, classText, classLabel, backpack, item1, item2, promo)
   {
      this.unitBoxes[index].setIndex(index);
      this.unitBoxes[index].setContainer(this);
      this.unitBoxes[index].SetUnitInfo(status,unitName,nickname,classText,classLabel,backpack,item1,item2,promo);
      this.unitBoxes[index].realize();
      this._parent.scroll(0);
   }
   function SetAddUnitText(index, displayString, prefix, icon)
   {
      this.unitBoxes[index].setIndex(index);
      this.unitBoxes[index].setContainer(this);
      this.unitBoxes[index].SetAddUnitText(displayString,prefix,icon);
      this.unitBoxes[index].SetHelp();
      this.unitBoxes[index].realize();
      this._parent.scroll(0);
   }
   function SetSelected(targetIndex, forceRedrawIfPreviouslySelected)
   {
      if((targetIndex == undefined || this.currentSelection == targetIndex) && !forceRedrawIfPreviouslySelected)
      {
         return undefined;
      }
      var _loc2_ = 0;
      while(_loc2_ < SquadList.MAX_UNITS)
      {
         this.unitBoxes[_loc2_].onLoseFocus();
         _loc2_ = _loc2_ + 1;
      }
      var _loc5_;
      var _loc6_;
      if(targetIndex > -1 && targetIndex < SquadList.MAX_UNITS)
      {
         _loc5_ = this.unitBoxes[targetIndex];
         if(!_loc5_.txtName._visible && _loc5_.txtAddUnit.text.length <= 1)
         {
            return undefined;
         }
         this.currentSelection = targetIndex;
         _loc5_.onReceiveFocus();
         _loc5_.SetHelp(this.help_icon0,this.help_display0,this.help_icon1,this.help_display1);
         _loc6_ = targetIndex - (3 + this._parent.offset);
         if(_loc6_ < 0)
         {
            this._parent.scroll(_loc6_);
         }
         else if(_loc6_ > 5)
         {
            this._parent.scroll(_loc6_ - 5);
         }
      }
   }
   function SetUnitHelp(icon0, display0, icon1, display1)
   {
      this.help_icon0 = icon0;
      this.help_icon1 = icon1;
      this.help_display0 = display0;
      this.help_display1 = display1;
   }
}
